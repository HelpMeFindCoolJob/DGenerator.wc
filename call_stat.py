# -*- coding: utf-8 -*-

""" Подробная статистика телефонных соединений для конретного клиента либо транка/опреатора """

import utm_data
import custom_exceptions
import datetime
from os import path, listdir, makedirs
from jinja2 import Environment, FileSystemLoader

class StatWorker():

    def __init__(self, config, period):
        try:
            self.config = config
            self.period = period
            self.period_dirname = '%s_%s' % tuple(period)
            self.data = utm_data.Data(self.config)  # Объект для получения данных из БД
            self.cdr_upload_dir = path.join(path.normpath(self.config.get('CDR', 'SourceRootCdrDir')),
                                            self.period_dirname)
            self.client_dir = path.normpath(
                '%s/individual' % self.period_dirname)  # Директория для клиентских детализаций
            self.trunk_dir = path.join(path.normpath(self.config.get('TRUNKS', 'trunksdetailsdir')),
                                       self.period_dirname)  # Директория для детализаций по транкам
            self.client_details_path = path.join(
                path.normpath(self.config.get('DETAILS', 'fulldetailsdir')),
                self.client_dir)  # Путь к детализациям клиентов
            self.trunks_details_path = path.join(
                path.normpath(self.config.get('DETAILS', 'fulldetailsdir')),
                self.trunk_dir)  # Путь к детализациям транков
            self.converted_cdr_path = path.join(path.normpath(self.config.get('CDR', 'sourcerootcdrdir')),
                                                self.period_dirname)
            self.client_detail_template_path = path.normpath(self.config.get('DETAILS', 'fulldetailtemplatepath'))
            self.trunks_template = path.normpath(self.config.get('TRUNKS', 'templatereportspath'))

            self.rt_trunks_info = self.config.get('TRUNKS', 'rostelekomtrunks')  # Инфо о транках Ростелекома
            self.beelinr_trunks_info = self.config.get('TRUNKS', 'beelinetrunks')  # Инфо о транках Билайна
        except Exception as exc:
            print('ERROR: Ошибка конфигурации либо повреждены жизненно важные файлы приложения. '
                  'Дальнейшая работа невозможна Причина - %s. Проверьте журнал для получения информации.' % exc)

    def get_client_stat(self, account):
        try:
            if path.isdir(self.cdr_upload_dir) and len(listdir(self.cdr_upload_dir)) != 0:
                client_stat = self.data.get_client_phone_number(account)
                client_name = ''
                all_calls = []  # Список всех dict данных о звонках, связанных с клиентом
                all_clients_numbers = []  # Список всех вариантов номеров, принадлежащих клиенту

                if not client_stat:
                    print('INFO: Информация о клиенте с аккаунтом %s не найдена. Проверьте корретность вводимой информации.'
                          % account)
                    return
                elif len(client_stat) == 1: # У клиента за лицевым счетом закреплен только 1 теелфонный номер
                    info_from_list = client_stat[0].split('|')
                    client_name = client_stat[0].split('|')[0]
                    base_number = info_from_list[2]
                    full_number = '49645%s' % base_number if len(base_number) == 5 else '496%s' % base_number
                    alt_number = base_number[2:] if len(base_number) == 7 else '45%s' % base_number
                    all_clients_numbers += [base_number, full_number, alt_number]
                elif len(client_stat) > 1:  #  У клиента за лицевым счетом закреплено более 1 телефонного номера
                    client_name = client_stat[0].split('|')[0]
                    for info_str in client_stat:  # Собираем все номера клиента в один список
                        info_list = info_str.split('|')
                        base_number = info_list[2]
                        full_number = '49645%s' % base_number if len(base_number) == 5 else '496%s' % base_number
                        alt_number = base_number[2:] if len(base_number) == 7 else '45%s' % base_number
                        all_clients_numbers += [base_number, full_number, alt_number]

                for cdr in listdir(self.cdr_upload_dir):
                    for line in open(path.join(self.cdr_upload_dir, cdr), 'r'):
                        calls_info = line.split(' ')
                        if calls_info[1] in all_clients_numbers or calls_info[3] in all_clients_numbers:
                            all_calls.append({
                                'numA': calls_info[1],
                                'numB': calls_info[3],
                                'date': calls_info[4] + calls_info[5],
                                'duration': calls_info[6],
                                'closeCode': calls_info[7]
                            })

                if not all_calls:
                    print('INFO: У клиента с аккаунтом %s отсутсвуют телефонные соединения за указанный период.'
                          % account)
                    return

                if not self.client_detail_template_path:
                    raise custom_exceptions.NotTemplateFileException

                if not path.isdir(self.client_details_path):
                    makedirs(self.client_details_path)

                jinja_env = Environment(
                    autoescape=False,
                    loader=FileSystemLoader(path.dirname(self.client_detail_template_path)),
                    trim_blocks=False
                )  # Окружение для шаблонизатора Jinja2

                filename = path.join(self.client_details_path, 'Full_detail_for_%s.html' % account)

                period_datetime = datetime.datetime(int(self.period[1]), int(self.period[0]), 1)

                context = {
                    'name': client_name,
                    'period': period_datetime.strftime('%B %Y'),
                    'callsCount': len(all_calls),
                    'calls': all_calls
                }  # Переменные для шаблонищатора
                html = jinja_env.get_template(path.basename(self.client_detail_template_path)).render(
                    context)  # Строковое представление отрендерренного шаблона
                # Секция сохранения файла детализации клиенту
                stat = open(filename, 'w+', encoding='utf-8')
                stat.writelines(html)
            else:
                raise custom_exceptions.NoUploadDirException
        except custom_exceptions.NoUploadDirException:
            print('ERROR: Не обнаружен каталог с CDR файлами либо файлы в каталоге, которые необходимо обработать')
        except custom_exceptions.NotTemplateFileException:
            print('ERROR: Некорректный шаблон полной детализации телефонных соединений пользователя. '
                  'Проверьте конфигурацию и структуру файла шаблона. Возможно файл шаблона отсутствует.')
        except Exception as exc:
            print('ERROR: Ошибка при генерировании полной статистики клиента. Причина - %s. '
                  'Проверьте журнал для получения информации.' % exc)
        else:
            print('COMPLITE: Полная статистика по вызовам для клиента с аккаунтом - %s успешно сгененирована.' % account)

    def get_trunks_stat(self):
        try:
            rt_trunks = {t.rstrip() for t in self.rt_trunks_info.split(',')}  # Признаки транков Ростелекома на моккутаторе
            beeline_trunks = {t.rstrip() for t in self.beelinr_trunks_info.split(',')}  # Признаки транков билайна

            if path.isdir(self.cdr_upload_dir) and len(listdir(self.cdr_upload_dir)) != 0:
                if not self.trunks_template:
                    raise custom_exceptions.NotTemplateFileException

                if not path.isdir(self.trunks_details_path):
                    makedirs(self.trunks_details_path)

                total_rt_trunk_stat = {
                    'calls_to' : [],
                    'calls_count_to' : 0,
                    'duration_to' : 0,
                    'calls_from' : [],
                    'calls_count_from' : 0,
                    'duration_from' : 0,
                    'report_file_path' : path.join(self.trunks_details_path, 'Rostelekom_info.html'),
                    'to_calls_file_path' : path.join(self.trunks_details_path, 'To_Rostelekom_calls.log'),
                    'from_calls_file_path' : path.join(self.trunks_details_path, 'From_Rostelekom_calls.log')
                }  # Объект с данными тарфика на транке Ростелекома
                total_beeline_trunk_stat = {
                    'calls_to': [],
                    'calls_count_to' : 0,
                    'duration_to': 0,
                    'calls_from': [],
                    'calls_count_from' : 0,
                    'duration_from': 0,
                    'report_file_path': path.join(self.trunks_details_path, 'Beeline_info.html'),
                    'to_calls_file_path': path.join(self.trunks_details_path, 'To_Beeline_calls.log'),
                    'from_calls_file_path': path.join(self.trunks_details_path, 'From_Beeline_calls.log')
                }  # Объект с данными тарфика на транке Биалйна

                for index, cdr in enumerate(listdir(self.cdr_upload_dir), start=1):
                    for line in open(path.join(self.cdr_upload_dir, cdr), 'r'):
                        cdr_info = line.split(' ')
                        duration = int(cdr_info[6])
                        trunk_a = cdr_info[0][1:6]; trunk_b = cdr_info[2][:5]  # Определяем исходящий и входящий транки
                        if trunk_a in rt_trunks and duration > 0:  # Входящий вызов из транков Ростелекома
                            total_rt_trunk_stat['calls_from'].append(line)
                            total_rt_trunk_stat['calls_count_from'] += 1
                            total_rt_trunk_stat['duration_from'] += duration
                            continue
                        elif trunk_b in rt_trunks and duration > 0:  # Исходящий вызов в Ростелеком
                            total_rt_trunk_stat['calls_to'].append(line)
                            total_rt_trunk_stat['calls_count_to'] += 1
                            total_rt_trunk_stat['duration_to'] += duration
                            continue
                        elif trunk_a in beeline_trunks and duration > 0:  # Входящий вызов из транков Билайна
                            total_beeline_trunk_stat['calls_from'].append(line)
                            total_beeline_trunk_stat['calls_count_from'] += 1
                            total_beeline_trunk_stat['duration_from'] += duration
                            continue
                        elif trunk_b in beeline_trunks and duration > 0:  # Исходящий вызов в Билайн
                            total_beeline_trunk_stat['calls_to'].append(line)
                            total_beeline_trunk_stat['calls_count_to'] += 1
                            total_beeline_trunk_stat['duration_to'] += duration
                    print('INFO: Файл %s из %s (%s) успешно обработан' %
                          (index, len(listdir(self.cdr_upload_dir)), cdr))

                    # Шаблонизируем данные в html
                    period_datetime = datetime.datetime(int(self.period[1]), int(self.period[0]), 1)
                    operators_data = {'Ростелеком' : total_rt_trunk_stat, 'Вымпелком' : total_beeline_trunk_stat}

                    jinja_env = Environment(
                        autoescape=False,
                        loader=FileSystemLoader(path.dirname(self.client_detail_template_path)),
                        trim_blocks=False
                    )  # Окружение для шаблонизатора Jinja2

                    for key, value in operators_data.items():
                        # Данные для шаблонизатора
                        context = {
                            'operator': key,
                            'period': period_datetime.strftime('%B %Y'),
                            'toDuration': '%.2f' % (value['duration_to'] / 60),
                            'toCalls': value['calls_count_to'],
                            'fromDuration': '%.2f' % (value['duration_from'] / 60),
                            'fromCalls': value['calls_count_from']
                        }
                        html = jinja_env.get_template(path.basename(self.trunks_template)).render(
                            context)  # Строковое представление отрендерренного шаблона
                        report = open(value['report_file_path'], 'w+', encoding='utf-8')
                        report.writelines(html)

                        # Текстовые файлы со списком всез телефонных соединений по транкам и направлениям
                        to_calls = open(value['to_calls_file_path'], 'w+', encoding='utf-8')
                        to_calls.writelines(value['calls_to'])
                        from_calls = open(value['from_calls_file_path'], 'w+', encoding='utf-8')
                        from_calls.writelines(value['calls_from'])
            else:
                raise custom_exceptions.NoUploadDirException
        except custom_exceptions.NoUploadDirException:
            print('ERROR: Не обнаружен каталог с CDR файлами либо файлы в каталоге, которые необходимо обработать')
        except custom_exceptions.NotTemplateFileException:
            print('ERROR: Некорректный шаблон для отчета о транках. Проверьте конфигурацию и структуру файла шаблона.'
                             ' Возможно файл шаблона отсутствует.')
        except Exception as exc:
            print('ERROR: Ошибка при генерировании статистики по транкам. Причина - %s. '
                  'Проверьте журнал для получения информации.' % exc)
        else:
            print('COMPLITE: Полная детализация телефонного трафика по транкам / операторам успешно сгененирована.')