# -*- coding: utf-8 -*-

""" Модуль для конвертирования CDR записей, трансфера их на сервер UTM5 и запуска утилиты utm5_send_cdr для обсчета
 переданных и сконвертированных CDR файлов"""

import utm_connect
import custom_exceptions
import subprocess
from os import path, listdir, makedirs

class Cdr:
    def __init__(self, period, config, connection=None):
        try:
            self.status = {
                'convert': 'READY',
                'transfer': 'READY',
                'parse': 'READY'
            }
            self.config = config
            self.connection = connection
            self.period = '%s_%s' % tuple(period)
            self.cdr_upload_dir = path.join(path.normpath(self.config.get('CDR', 'SourceRootCdrDir')), self.period)
            self.cdr_converted_dir = path.join(path.normpath(self.config.get('CDR', 'ConvertedRootCdrDir')),
                                               self.period)
            self.remote_cdr_dir = path.join(self.config.get('CDR', 'RemotePath'), self.period)
            self.parser = self.config.get('CDR', 'ParserPath')
            self.parser_config = self.config.get('CDR', 'ParserConfigPath')
            self.cut_big_cdr = self.config.get('CDR', 'splitcdr')
            self.max_lines_when_cut_cdr = self.config.get('CDR', 'maxlinesincdr')
        except Exception as exc:
            print('ERROR: Ошибка конфигурации либо повреждены жизненно важные файлы приложения. '
                  'Дальнейшая работа невозможна Причина - %s. Проверьте журнал для получения информации.' % exc)

    def convert(self): # Преобразовать CDR в формат UTM5
        try:
            if path.isdir(self.cdr_upload_dir) and len(listdir(self.cdr_upload_dir)) != 0:
                if not path.isdir(self.cdr_converted_dir):
                    makedirs(self.cdr_converted_dir)

                for index, cdr in enumerate(listdir(self.cdr_upload_dir), start=1):
                    converted_cdr_name = cdr.replace('.log', '.cdr')
                    converted_cdr_lines = []
                    line_count = 0 # Счетсчик строк в файле
                    file_part_count = 1  # Счетчик частей файлов
                    for line in open(path.join(self.cdr_upload_dir, cdr)):
                        temp = line.split()
                        converted_cdr_lines.append(
                            '%s;%s;%s;%s;%s %s;%s;%s;1\n' %
                            (temp[1], temp[3], temp[6], str(line_count), temp[4], temp[5], temp[0][1:], temp[2]))
                        line_count += 1

                        if self.cut_big_cdr == '1':
                            # Если в файле слишком много строк (с большими фалойами возникает проблема с зависанием channek-а paramiko при большом stdout) разбиваем его на части
                            if len(converted_cdr_lines) == int(self.max_lines_when_cut_cdr):
                                converted_cdr_file = open(path.join(self.cdr_converted_dir, converted_cdr_name), 'w+')
                                converted_cdr_file.writelines(converted_cdr_lines)
                                if file_part_count == 1:
                                    converted_cdr_name = converted_cdr_name.replace('.cdr',
                                                                                '_%s.cdr' % file_part_count)
                                else:
                                    converted_cdr_name = converted_cdr_name.replace('_%s.cdr' % str(file_part_count-1),
                                                                                '_%s.cdr' % file_part_count)
                                converted_cdr_lines =[]
                                file_part_count += 1

                    converted_cdr_file = open(path.join(self.cdr_converted_dir, converted_cdr_name), 'w+')
                    converted_cdr_file.writelines(converted_cdr_lines)
                    print('INFO: Файл %s из %s (%s) успешно сконвертирован' %
                                     (index, len(listdir(self.cdr_upload_dir)), cdr))
                    # cdr_count += 1
            else:
                raise custom_exceptions.NoUploadDirException
        except custom_exceptions.NoUploadDirException:
            print('ERROR: Не обнаружен каталог с CDR файлами либо файлы в каталоге, которые необходимо обработать')
            self.status['convert'] = 'ERROR'
        except Exception as exc:
            print('ERROR: Ошибка при работе с CDR. Дальнейшее конвертирование невозможно.'
                  'Причина - %s. Проверьте журнал для получения информации.' % exc)
            self.status['convert'] = 'ERROR'
        else:
            print('COMPLETE: Все CDR файлы успешно сконвертированы.')
            self.status['convert'] = 'DONE'

    def transfer(self):  # Передать сконвертированные файлы на сервер с UTM
        try:
            self.convert()
            if self.status == 'ERROR':
                return

            all_local_paths = [path.join(self.cdr_converted_dir, cdr) for cdr
                               in listdir(self.cdr_converted_dir)]  # Список абсолютных путей к локальным CDR файлам
            # for cdr in listdir(self.cdr_converted_dir):
            #     all_local_paths.append(path.join(self.cdr_converted_dir, cdr))

            if self.status['convert'] == 'DONE' and len(all_local_paths) > 0:
                self.connection.cdr_transfer(all_local_paths, self.remote_cdr_dir)
                print('COMPLETE: Все CDR файлы успешно переданы на сервер.')
                self.status['transfer'] = 'DONE'
            else:
                print('ERROR: Сконвертированные CDR файлы недостпуны или не существуют.'
                      'Невозможно отправить CDR файлы на сервер.')
                self.status['transfer'] = 'ERROR'
        except Exception as exc:
            print('ERROR: Ошибка при работе с CDR. Передача файлов невозможна.'
                  'Причина - %s. Проверьте журнал для получения информации.' % exc)

    def parse(self): # Пропарсить переданные CDR файлы, запустив на сервере утилиту utm5_send_cdr
        try:
            self.transfer()
            if self.status['transfer'] == 'ERROR':
                return

            all_cdr = ['%s/%s' %(self.period, cdr) for cdr in listdir(self.cdr_converted_dir)]

            if self.status['transfer'] == 'DONE' and len(all_cdr) > 0:
                self.connection.execute_parse_command(all_cdr)
            else:
                print('ERROR: Сконвертированные CDR файлы недостпуны или не существуют.'
                      'Невозможно начать парсинг файлов на сервере.')
                self.status['transfer'] = 'ERROR'
        except Exception as exc:
            print('ERROR: Ошибка при инициализации парсинга CDR. Дальнейшая работа невозможна.'
                  'Причина - %s. Проверьте журнал для получения информации.' % exc)
            self.status['parse'] = 'ERROR'
        else:
            print('COMPLETE: Все CDR файлы успешно пропарсились на сервере.')
            self.status['parse'] = 'DONE'

    def cut_big_cdr(self, cdr):
        try:
            pass
        except Exception as exc:
            print('ERROR: Ошибка во время сегментации CDR файла (%s)' % cdr)
