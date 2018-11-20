# -*- coding: utf-8 -*-

""" Generate HTML and CSV doucments from utm_data class objects """

import utm_data
import qr_code
import datetime
import calendar
import custom_exceptions
from os import path, makedirs
from jinja2 import Environment, FileSystemLoader

class DocsGenerator():
    # user_groups - 65 Физические лица, 66 юридические. Зависит от ID тарифа, если поменяли тариф, поменяйте признак группы

    def __init__(self, period, config, start_bill_number = 0):
        try:
            self.period = period
            self.period_datetime = datetime.datetime(int(self.period[1]), int(self.period[0]), 1)
            self.curr_docs_dir = '%s_%s' % tuple(period)
            self.config = config
            self.bill_template = path.normpath(self.config.get('BILLS', 'TemplatePath'))  # Путь к шаблону для квитанций
            self.bills_dir = path.join(path.normpath(self.config.get('BILLS', 'BillsDir')),
                                       self.curr_docs_dir)  # Путь гд будут лежать все квитанции
            self.detail_template = path.normpath(
                self.config.get('DETAILS', 'TemplatePath'))  # Путь к шаблону для детализаций
            self.details_dir = path.join(path.normpath(self.config.get('DETAILS', 'DeatildsDir')),
                                         self.curr_docs_dir)  # Путь где будут лежать все детализации
            self.reports_dir = path.join(path.normpath(self.config.get('REPORTS', 'ReportsDir')),
                                         self.curr_docs_dir)  # Путь где будут лежать отчеты
            self.number_bill_for_b2breport = \
                int(start_bill_number) if start_bill_number > 0 else int(self.config.get('REPORTS', 'BillCounter'))
            self.data = utm_data.Data(self.config)
        except Exception as exc:
            print('ERROR: Ошибка конфигурации либо повреждены жизненно важные файлы приложения. '
                  'Дальнейшая работа невозможна Причина - %s. Проверьте журнал для получения информации.' % exc)

    # Секция для генерирования отчетов
    def generate_reports(self):
        try:
            if not path.isdir(self.reports_dir):
                makedirs(self.reports_dir)
            stats = self.data.get_all_stats(self.period)
            if not stats:
                raise custom_exceptions.BadStatsException

            last_day = calendar.monthrange(int(self.period[1]), int(self.period[0]))[1]
            period_b2b = datetime.datetime(int(self.period[1]), int(self.period[0]), last_day)
            period_b2b_report_str = period_b2b.strftime('%d.%m.%Y %H:%M')

            b2b_report_count = 0 # Номер по порядку для отчета в Билайн, enumerate как-то не пошел, еще не разбирался почему

            legal_clients_report_filename = 'legal_clients_report.csv'  # Файл в который сохраняются отчеты юр лица
            civil_clients_report_filename = 'civil_clients_report.csv'  # Файл в который сохраняются отчеты физ лица
            b2b_period_month = int(self.period[0]) + 1 if int(self.period[0]) < 12 else 1  #
            b2b_period_year = int(self.period[1]) + 1 if int(self.period[0]) == 12 else int(self.period[1])  #
            beeline_report_filename = 'GW_BIL_{:04}_{:02}.csv'.format(
                b2b_period_year, b2b_period_month
            )  # Файл в который сохраняются отчеты b2b для Вымплекома
            report_to_1c_filname = 'report_to_1c.csv'  # Файл в который сохраняются b2b отчеты для бухгалтерии

            legal_clients_report = [
                'Номер договора;Название организации;Сумма межгорода без НДС;Сумма межгорода с НДС\n'
            ] # Список строк для отчета юр лица
            civil_clients_report = [
                'Номер счета;ФИО;Сумма межгорода\n'
            ] # Список стриок для отчета физ лица
            beeline_report = [] # Список строк для отчета b2b для Вымплекома
            report_to_1c = [
                 # period_b2b.strftime('Отчет по МГ/МН переговорам за %B $Y;;;;;;;;;;;;;;;;\n')
                'Отчет по МГ/МН переговорам за %s %s;;;;;;;;;;;;;;;;\n' % tuple(self.period)
            ] # Список строк для отчета b2b для бухгалтерии

            all_legal_clients_mg_summ = 0.0 # Итоговая сумма для всех юр лиц без НДС
            all_legal_clients_mg_summ_with_tax = 0.0  # Итоговая сумма для всех юр лиц с НДС
            all_civil_clients_mg_summ_with_tax = 0.0  # Итоговая сумма для всех физ лиц с НДС

            all_legal_cost = {10 : 0, 12 : 0, 14 : 0}  # Суммарные стоимости физ лиц на каждое направление для Билайна (ЗН-10, МГ-12, МН-14)
            all_legal_dur = {10 : 0, 12 : 0, 14 : 0}  # Суммарные длительность (в минутах) физ лиц на каждое направление для Билайна (ЗН-10, МГ-12, МН-14)

            for key, value in stats.items():
                client_stat = value
                account = key

                if client_stat[5] == '65':  # Если клиент имеет id тарифа 65 - то это юридическое лицо
                    contract = client_stat[4]; name = client_stat[1]; mg_summ = client_stat[8]
                    mg_summ_with_tax = client_stat[9]
                    # Секция общего отчета юр лица
                    legal_clients_report.append(
                        '%s;%s;%s;%s\n' % (contract, name, mg_summ, mg_summ_with_tax)
                    )
                    all_legal_clients_mg_summ += float(mg_summ)
                    all_legal_clients_mg_summ_with_tax += float(mg_summ_with_tax)

                    # Секция b2b отчета юр лица

                    bill_num_b2b_str = 'GW#{:06}'.format(self.number_bill_for_b2breport)
                    sorted_calls = {}  # Сгруппированные по зонам (ЗН-10 МГ-12 МН-14) вызовы клиента
                    if len(client_stat[6]) > 0:
                        sorted_calls = self.sort_calls(client_stat[6])
                    for key, value in sorted_calls.items():
                        if value[0] == 0:
                            continue
                        b2b_report_count += 1
                        beeline_report.append(
                            '%s;H4393;%s;%s;;%s;%s;0;2;%s;%s;%.2f;%s;46 465;1\n' %
                            (b2b_report_count, client_stat[4], bill_num_b2b_str, period_b2b_report_str,
                             period_b2b_report_str, key, period_b2b_report_str, value[0] * 1.18, value[1])
                        )
                        report_to_1c.append(
                            '%s;%s;%s;%s;%.2f;%s;%s;%.2f;;;;;;;;;\n' %
                            (client_stat[4], bill_num_b2b_str, name,len(client_stat[6]),
                             value[0], value[1], key, value[0] * 1.18)
                        )
                    if len(client_stat[6]) > 0:
                        self.number_bill_for_b2breport += 1

                else:  # Если нет, значит он физическое лицо

                    name = client_stat[1]; mg_summ = client_stat[8]
                    # Секция общего отчета физ лица лица
                    civil_clients_report.append(
                        '%s;%s;%s\n' % (account, name, mg_summ)
                    )
                    all_civil_clients_mg_summ_with_tax += float(mg_summ)

                    # Секция b2b отчета физ лица
                    if len(client_stat[6]) > 0:
                        sorted_calls = self.sort_calls(client_stat[6]) # Сгруппированные по зонам (ЗН-10 МГ-12 МН-14) вызовы клиента
                        for i in range (10, 16, 2): # Проходим по каждому из групп направлений (ЗН-10 МГ-12 МН-14)
                            all_legal_cost[i] += sorted_calls[str(i)][0]
                            all_legal_dur[i] += sorted_calls[str(i)][1]
                print('INFO: Информация об аккаунте %s успешно обработана' % (account))

            # Формируем суммирующую строку всех физ лиц для b2b отчета
            for i in range(10, 16, 2): # Проходим по каждому из групп направлений (ЗН-10 МГ-12 МН-14)
                b2b_report_count += 1
                bill_num_b2b_str = 'GW#{:06}'.format(self.number_bill_for_b2breport)
                beeline_report.append(
                    '%s;H4393;GW#99999;%s;;%s;%s;0;2;%s;%s;%.2f;%s;46 465;1\n' %
                    (b2b_report_count, bill_num_b2b_str, period_b2b_report_str,
                     period_b2b_report_str, i, period_b2b_report_str, all_legal_cost[i], all_legal_dur[i])
                )
                report_to_1c.append(
                    'GW#99999;%s;Физические лица;;%.2f;%s;%s;%.2f;;;;;;;;;\n' %
                    (bill_num_b2b_str, all_legal_cost[i], all_legal_dur[i], i, all_legal_cost[i] * 1.18)
                )
            self.number_bill_for_b2breport += 1 # ПОТЕНЦИАЛЬНО ДЛЯ СОХРАНЕНИЯ НОМЕРА СЧЕТА

            # Формируем итоговую строку для общих отчетов
            legal_total_line = ';;Итого сумма межгорода без НДС составляет;{0:.2f}\n' \
                               ';;Итого сумма межгорода с НДС составляет;{1:.2f}'.format(
                all_legal_clients_mg_summ, all_legal_clients_mg_summ_with_tax)

            legal_clients_report.append(legal_total_line)
            civil_total_line = ';;Итого сумма межгорода;{0:.2f}'.format(
                all_civil_clients_mg_summ_with_tax)
            civil_clients_report.append(civil_total_line)

            # Формируем итоговую строку для отчета в бухгалтерию
            report_to_1c_ilne = ';;Итого Юр. лица без ндс;;%.2f;;;;;;;;;;;;\n' \
                                ';;Итого Юр. лица с ндс;;%.2f;;;;;;;;;;;;\n' \
                                ';;Итого Физ. лица;;%.2f;;;;;;;;;;;;\n' \
                                ';;;;;;;;;;;;;;;;\n' \
                                ';;;;;;;;;;;;;;;;\n' \
                                'Разработал___________________Стулов А.А.;;;;;;;;;;;;;;;;\n' \
                                ';;;;;;;;;;;;;;;;\n' \
                                ';;;;;;;;;;;;;;;;\n' \
                                ';;;;;;;;;;;;;;;;\n' \
                                ';;;;;;;;;;;;;;;;' % \
                                (all_legal_clients_mg_summ, all_legal_clients_mg_summ_with_tax,
                                 all_civil_clients_mg_summ_with_tax)
            report_to_1c.append(report_to_1c_ilne)

            # Сохраняем файл отчета юр лица
            legal_clients_report_file = open(path.join(self.reports_dir, legal_clients_report_filename), 'w+')
            legal_clients_report_file.writelines(legal_clients_report)

            # Сохраняем файл отчета физ лица
            civil_clients_report_file = open(path.join(self.reports_dir, civil_clients_report_filename), 'w+')
            civil_clients_report_file.writelines(civil_clients_report)

            # Сохраняем файл отчета для Билайна
            beeline_report_filename = open(path.join(self.reports_dir, beeline_report_filename), 'w+')
            beeline_report_filename.writelines(beeline_report)

            # Сохраняем файл отчета для Бухгалтерии
            report_to_1c_filname = open(path.join(self.reports_dir, report_to_1c_filname), 'w+')
            report_to_1c_filname.writelines(report_to_1c)

            # Сохраняем номер счета для 1С
            self.save_1c_bill_number(self.number_bill_for_b2breport)

        except custom_exceptions.BadStatsException:
            print('ERROR: Невозможно получить список клиентов. Генерирование отчетов невозможно.')
        except Exception as exc:
            # Add exc in log file
            print('ERROR: Ошибка при создании отчета. Причина - %s. Проверьте журнал для получения информации.'
                  % exc)
        else:
            print('COMPLETE: Все отчеты успешно сгенерированы.')

    # Секция для генерирования детализаций и квитанций всем клиентам с МГ/МН/ЗН связью
    def generate_bills(self): # Генерируем квитанции клиентов
        try:
            if not self.bill_template:
                raise custom_exceptions.NotTemplateFileException

            if not path.isdir(self.bills_dir):
                makedirs(self.bills_dir)

            jinja_env = Environment(
                autoescape=False,
                loader=FileSystemLoader(path.dirname(self.bill_template)),
                trim_blocks=False
            ) # Окружение для шаблонизатора Jinja2

            # period = '%s %s г.' % (self.get_ru_month(int(self.period[0])), self.period[1]) # Костыль для представления месяца в русской локали
            period = self.period_datetime.strftime('%B %Y г.')

            stats = self.data.get_all_stats(self.period) # Получаем статистику каждого клиента

            if not stats:
                raise custom_exceptions.BadStatsException

            for key, value in stats.items():
                client_stat = value

                if client_stat[5] == '66': # Если клиент имеет id тарифа 66 - то это физическое лицо
                    name = client_stat[1]; mg_summ = client_stat[8];address = client_stat[2];rent_summ = client_stat[7]
                    total_summ = client_stat[10]
                    file_name = path.join(self.bills_dir, '%s.html' % (key))
                    if len(client_stat[3]) > 0: # Проверяем наличие отлельного значения квартиры, если есть, форматируем строку с адресом.
                        address += ' кв. %s' % (client_stat[3])
                    splited_name = name.split() # Имя в представлении для QR кода

                    if len(splited_name) > 1:
                        last_name, first_name, *middle_name = splited_name
                        if isinstance(middle_name, list):
                            middle_name = ' '.join(middle_name)
                    else:
                        print(
                            'ERROR: Невозможно сгенерировать QR-код для %s. Проверьте и исправьте ФИО клиента.' % key)
                        return

                    qr = qr_code.QR_generator(
                        key,
                        'ST00012|Name=ООО «Альтес-Р»|PersonalAcc=40702810740460000716|BankName=ПАО Сбербанк|'
                        'BIC=044525225|CorrespAcc=30101810400000000225|PAYEEINN=5055002574|KPP=505501001|LastName=%s|'
                        'FirstName=%s|MiddleName=%s|PayerAddress=%s' %
                        (last_name, first_name, str(middle_name), address),
                        self.bills_dir
                    ).generate_qr_code() # Получем текст с описанием тэга img для вставки в шаблон

                    if qr == 'ERROR':
                        raise custom_exceptions.BadQrException

                    context = {
                        'date' : period,
                        'account' : key,
                        'user' : name,
                        'address' : address,
                        'qr_image_tag' : qr,
                        'mgsumm' : mg_summ,
                        'abonsumm' : rent_summ,
                        'summary' : total_summ
                    } # Переменные для шаблонищатора
                    html = jinja_env.get_template(path.basename(self.bill_template)).render(
                        context)  # Строковое представление отрендерренного шаблона
                    # Секция сохранения файла детализации клиенту
                    bill = open(file_name, 'w+', encoding='utf-8')
                    bill.writelines(html)
                    print('INFO: Квитанция для аккаунта %s успешно сгенерирована' % (key))

        except custom_exceptions.BadStatsException:
            print('ERROR: Невозможно получить список клиентов. Генерирование квитанций невозможно.')
        except custom_exceptions.NotTemplateFileException:
            print('ERROR: Некорректный шаблон для квитанции. Проверьте конфигурацию и структуру файла шаблона.'
                             ' Возможно файл шаблона отсутствует.')
        except custom_exceptions.BadQrException:
            print('ERROR: Ошибка формирования QR кода. Генерирование квитанций невозможно.')
        except Exception as exc:
            # Ведем лог
            print('ERROR: Ошибка при генерировании квитанций. Причина - %s. Проверьте журнал для получения информации.'
                  % exc)
        else:
            print('COMPLETE: Все квитанции пользователей успешно сгенерированы.')

    def generate_details(self): # Генерируем детализации звноков клиентов
        try:
            if not self.detail_template:
                raise custom_exceptions.NotTemplateFileException

            if not path.isdir(self.details_dir):
                makedirs(self.details_dir)

            jinja_env = Environment(
                autoescape=False,
                loader=FileSystemLoader(path.dirname(self.detail_template)),
                trim_blocks=False
            ) # Окружение для шаблонизатора Jinja2

            # period = '%s %s г.' % (self.get_ru_month(int(self.period[0])), self.period[1]) # Костыль для представления месяца в русской локали
            period = self.period_datetime.strftime('%B %Y г.')

            stats = self.data.get_all_stats(self.period)  # Получаем статистику каждого клиента
            if not stats:
                raise custom_exceptions.BadStatsException

            for key, value in stats.items():
                client_stat = value

                if len(client_stat[6]) > 0: # Проверяем есть ли у клиента ЗН/МГ/Мн соединения
                    contract = client_stat[4];name = client_stat[1];mg_summ = client_stat[8]
                    current_path = ''  # Путь к сгенерированным файлам детализации
                    if client_stat[5] == '66':
                        current_path = path.join(self.details_dir, 'civil')  # Путь для клиентов физических лиц
                    elif client_stat[5] == '65':
                        mg_summ = client_stat[9]  # Добавить НДС к итогово
                        current_path = path.join(self.details_dir, 'legal')  # Путь для клиентов юридических лиц
                    else:
                        current_path = self.details_dir  # Путь для всех остальных !!! ТЕСТ

                    if not path.isdir(current_path):
                        makedirs(current_path)

                    file_name = path.join(current_path, 'Detail_for_%s.html' % (key))
                    calls_list = []

                    for call in client_stat[6]:
                        call_info = call.split('|')
                        num_a = call_info[0];num_b = call_info[1];zone = call_info[2];duration = call_info[4];summ = call_info[6]
                        date = datetime.datetime.fromtimestamp(int(call_info[3])).strftime('%d.%m.%Y %H:%M:%S')
                        if client_stat[5] == '66':  # Если клиент физическое лицо
                            calls_list.append(
                                {'numA': num_a, 'numB': num_b, 'date': date, 'duration': duration, 'zone': zone,
                                 'sum': summ}
                            )
                        elif client_stat[5] == '65':  # Если клиент юридическое лицо
                            calls_list.append(
                                {'numA': num_a, 'numB': num_b, 'date': date, 'duration': duration, 'zone': zone,
                                 'sum': '{0:.2f}'.format(float(summ) * 1.18)}
                            )
                        else:
                            pass

                    context = {
                        'name' : name,
                        'period' : period,
                        'numDog' : contract,
                        'callsCount' : len(calls_list),
                        'amount' : mg_summ,
                        'calls' : calls_list
                    } # Переменные для шаблонищатора

                    html = jinja_env.get_template(path.basename(self.detail_template)).render(context) # Строковое представление отрендерренного шаблона
                    # Секция сохранения файла детализации клиенту
                    detail = open(file_name, 'w+', encoding='utf-8')
                    detail.writelines(html)
                    print('INFO: Детализация для аккаунта %s успешно сгенерирована' % (key))

        except custom_exceptions.BadStatsException:
            print('ERROR: Невозможно получить список клиентов. Генерирование детализаций невозможно.')
        except custom_exceptions.NotTemplateFileException:
            print('ERROR: Некорректный шаблон для детализаций. Проверьте конфигурацию и структуру файла шаблона.'
                             ' Возможно файл шаблона отсутствует.')
        except Exception as exc:
            # Ведем лог
            print('ERROR: Ошибка при генерировании детализаций. Причина - %s. Проверьте журнал для получения информации.'
                  % exc)
        else:
            print('COMPLETE: Все детализации пользователей успешно сгенерированы.')

    # Секция для генерирования детализаций и квитанций для конкретного пользователя (ID пользователя)
    def generate_detail_for_client(self, account): # Генерирует детализацию конкретному пользователю, исходя из account
        try:
            individual_detail_path = path.join(self.details_dir, 'individual')

            if not self.detail_template:
                raise custom_exceptions.NotTemplateFileException

            if not path.isdir(individual_detail_path):
                makedirs(individual_detail_path)

            jinja_env = Environment(
                autoescape=False,
                loader=FileSystemLoader(path.dirname(self.detail_template)),
                trim_blocks=False
            ) # Окружение для шаблонизатора Jinja2

            # period = '%s %s г.' % (self.get_ru_month(int(self.period[0])), self.period[1]) # Костыль для представления месяца в русской локали
            period = self.period_datetime.strftime('%B %Y г.')

            stats = self.data.get_stats_for_client(self.period, account)  # Получаем статистику выбранного клиента
            if not stats:
                raise custom_exceptions.BadStatsException

            client_stat = stats[account]

            if len(client_stat[6]) > 0:  # Проверяем есть ли у клиента ЗН/МГ/Мн соединения
                contract = client_stat[4];name = client_stat[1];mg_summ = client_stat[8]
                file_name = path.join(individual_detail_path, 'Detail_for_%s.html' % (account))
                calls_list = []

                for call in client_stat[6]:
                    call_info = call.split('|')
                    num_a = call_info[0];num_b = call_info[1];zone = call_info[2];duration = call_info[4];summ = call_info[6]
                    date = datetime.datetime.fromtimestamp(int(call_info[3])).strftime('%d.%m.%Y %H:%M:%S')
                    calls_list.append(
                        {'numA': num_a, 'numB': num_b, 'date': date, 'duration': duration, 'zone': zone, 'sum': summ}
                    )

                context = {
                        'name': name,
                    'period': period,
                    'numDog': contract,
                    'callsCount': len(calls_list),
                    'amount': mg_summ,
                    'calls': calls_list
                }  # Переменные для шаблонищатора

                html = jinja_env.get_template(path.basename(self.detail_template)).render(
                    context)  # Строковое представление отрендерренного шаблона
                # Секция сохранения файла детализации клиенту
                detail = open(file_name, 'w+', encoding='utf-8')
                detail.writelines(html)
            else:
                raise custom_exceptions.NotReasonGenerateDetailExceprion

        except custom_exceptions.BadStatsException:
            print('ERROR: Невозможно получить информацию  о клиенте. Генерирование детализации для %s невозможно.'
                  % account)
        except custom_exceptions.NotTemplateFileException:
            print('ERROR: Некорректный шаблон для детализаций. Проверьте конфигурацию и структуру файла шаблона.'
                ' Возможно файл шаблона отсутствует.')
        except custom_exceptions.NotReasonGenerateDetailExceprion:
            print('INFO: У клиента %s отсутствуют тарифицируемые теелфонные соединения. '
                  'Детализация не может быть сгенерирована' % account)
        except Exception as exc:
            # Ведем лог
            print('ERROR: Ошибка при генерировании детализации для %s. Причина - %s. '
                  'Проверьте журнал для получения информации.' % (account, exc))
        else:
            print('COMPLETE: Детализация пользователю %s успешно сгенерированы.' % account)

    def generate_bill_for_client(self, account):
        try:
            individual_detail_path = path.join(self.bills_dir, 'individual')

            if not self.detail_template:
                raise custom_exceptions.NotTemplateFileException

            if not path.isdir(individual_detail_path):
                makedirs(individual_detail_path)

            jinja_env = Environment(
                autoescape=False,
                loader=FileSystemLoader(path.dirname(self.detail_template)),
                trim_blocks=False
            )  # Окружение для шаблонизатора Jinja2

            # period = '%s %s г.' % (
            # self.get_ru_month(int(self.period[0])), self.period[1])  # Костыль для представления месяца в русской локали

            period = self.period_datetime.strftime('%B %Y г.')

            stats = self.data.get_stats_for_client(self.period, account)  # Получаем статистику выбранного клиента
            if not stats:
                raise custom_exceptions.BadStatsException

            client_stat = stats[account]

            if client_stat[5] == '66':  # Если клиент имеет id тарифа 66 - то это физическое лицо
                name = client_stat[1];mg_summ = client_stat[8];address = client_stat[2];rent_summ = client_stat[7]
                total_summ = client_stat[10];file_name = path.join(individual_detail_path, '%s.html' % (account))
                if len(client_stat[
                           3]) > 0:  # Проверяем наличие отлельного значения квартиры, если есть, форматируем строку с адресом.
                    address += ' кв. %s' % (client_stat[3])
                splited_name = name.split()  # Имя в представлении для QR кода

                # last_name = first_name = middle_name = ''
                if len(splited_name) > 1:
                    last_name, first_name, *middle_name = splited_name
                    if isinstance(middle_name, list):
                        middle_name = ' '.join(middle_name)
                else:
                    print('ERROR: Невозможно сгенерировать QR-код для %s. Проверьте и исправьте ФИО клиента.' % account)
                    return

                qr = qr_code.QR_generator(
                    account,
                    'ST00012|Name=ООО «Альтес-Р»|PersonalAcc=40702810740460000716|BankName=ПАО Сбербанк|'
                    'BIC=044525225|CorrespAcc=30101810400000000225|PAYEEINN=5055002574|KPP=505501001|LastName=%s|'
                    'FirstName=%s|MiddleName=%s|PayerAddress=%s' %
                    (last_name, first_name, middle_name, address),
                    individual_detail_path
                ).generate_qr_code()  # Получем текст с описанием тэга img для вставки в шаблон

                if qr == 'ERROR':
                    raise custom_exceptions.BadQrException

                context = {
                    'date': period,
                    'account': account,
                    'user': name,
                    'address': address,
                    'qr_image_tag': qr,
                    'mgsumm': mg_summ,
                    'abonsumm': rent_summ,
                    'summary': total_summ
                }  # Переменные для шаблонищатора
                html = jinja_env.get_template(path.basename(self.bill_template)).render(
                    context)  # Строковое представление отрендерренного шаблона
                # Секция сохранения файла детализации клиенту
                bill = open(file_name, 'w+', encoding='utf-8')
                bill.writelines(html)
        except custom_exceptions.BadStatsException:
            print('ERROR: Невозможно получить информацию о клиенте. Генерирование детализаций для %s невозможно.'
                             % account)
        except custom_exceptions.NotTemplateFileException:
            print('ERROR: Некорректный шаблон для детализаций. Проверьте конфигурацию и структуру файла шаблона.'
                             ' Возможно файл шаблона отсутствует.')
        except Exception as exc:
            # Ведем лог
            print('ERROR: Ошибка при генерировании квитанции для %s. Причина - %s. '
                  'Проверьте журнал для получения информации.' % (account, exc))
        else:
            print('COMPLETE: Квитанция пользователю %s успешно сгенерирована.' % account)


    # Секция для вспомогательных функций
    def sort_calls(self, calls): # Возвращает сумму и длительность всех вызовов у клиента: разбитую по группам для Билайна
        output = {'10':(), '12':(), '14':()} # 10-МН, 12-МГ, 14-ЗН
        call_10_cost = call_12_cost = call_14_cost = 0
        call_10_dur = call_12_dur = call_14_dur = 0
        for call in calls:
            info = call.split('|')
            if info[1][:4] == '8496':
                call_14_cost += float(info[6])
                call_14_dur += int(int(info[4]) / 60)
            elif info[1][:3] == '810':
                call_10_cost += float(info[6])
                call_10_dur += int(int(info[4]) / 60)
            else:
                call_12_cost += float(info[6])
                call_12_dur += int(int(info[4]) / 60)
        output['10'] = (call_10_cost, call_10_dur)
        output['12'] = (call_12_cost, call_12_dur)
        output['14'] = (call_14_cost, call_14_dur)
        return output

    # def get_ru_month(self, month): # Временный костыль для показа локализованного месяца, поскольку не разобрался с локалями
    #     months  = {
    #         1 : 'Январь',
    #         2 : 'Февраль',
    #         3 : 'Март',
    #         4 : 'Апрель',
    #         5 : 'Май',
    #         6 : 'Июнь',
    #         7 : 'Июль',
    #         8 : 'Август',
    #         9 : 'Сентябрь',
    #         10 : 'Октябрь',
    #         11 : 'Ноябрь',
    #         12 : 'Декабрь'
    #     }
    #     return months[month]

    def save_1c_bill_number(self, number):  # Устанавливает соответствующее значние в конфиге для номре асчета 1С
        self.config.set('REPORTS', 'BillCounter', str(number))