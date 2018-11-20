# -*- coding: utf-8 -*-

""" Получение данных из UTM5, выполнение SQL-запросов. Формирование структур, которые будут переданы генератору
 документов"""

import mysql.connector
import datetime
import calendar
import custom_exceptions
from sys import stdout as cmd_output

class Data():
    def __init__(self, config):
        try:
            self.queries = {
                'client-info-id':
                    'SELECT users_accounts.account_id, users.login, users.full_name, users.actual_address, '
                    'users.flat_number, users.comments, account_tariff_link.tariff_id '
                    'FROM users, users_accounts, account_tariff_link '
                    'WHERE users.id = users_accounts.uid '
                    'AND users_accounts.account_id = account_tariff_link.account_id '
                    'AND (account_tariff_link.tariff_id = 66 OR account_tariff_link.tariff_id = 65) '
                    'AND users.is_deleted = 0 '
                    'AND account_tariff_link.is_deleted = 0 '
                    'AND users_accounts.account_id = %s;',
                'clients_list':
                    'SELECT users_accounts.account_id, users.login, users.full_name, users.actual_address, '
                    'users.flat_number, users.comments, account_tariff_link.tariff_id '
                    'FROM users, users_accounts, account_tariff_link '
                    'WHERE users.id = users_accounts.uid '
                    'AND users_accounts.account_id = account_tariff_link.account_id '
                    'AND (account_tariff_link.tariff_id = 66 OR account_tariff_link.tariff_id = 65) '
                    'AND users.is_deleted = 0 '
                    'AND account_tariff_link.is_deleted = 0;',
                'client-calls':
                    'SELECT tel_sessions_log.Calling_Station_Id, tel_sessions_log.Called_Station_Id, tel_zones_v2.name, '
                    'tel_sessions_log.session_start_date, tel_sessions_detail.duration, tel_sessions_detail.base_cost, '
                    'tel_sessions_detail.sum_cost '
                    'FROM tel_sessions_log, tel_sessions_detail, tel_zones_v2 '
                    'WHERE tel_sessions_log.id = tel_sessions_detail.dhs_sess_id '
                    'AND tel_sessions_log.account_id = %s '
                    'AND tel_sessions_log.zone_id = tel_zones_v2.id '
                    'AND tel_sessions_log.session_start_date >= %s '
                    'AND tel_sessions_log.session_start_date < %s;',
                'mg-summ':
                    'SELECT SUM(tel_sessions_detail.sum_cost) AS total '
                    'FROM tel_sessions_log, tel_sessions_detail, tel_zones_v2 '
                    'WHERE tel_sessions_log.id = tel_sessions_detail.dhs_sess_id '
                    'AND tel_sessions_log.account_id = %s '
                    'AND tel_sessions_log.zone_id = tel_zones_v2.id '
                    'AND tel_sessions_log.session_start_date >= %s '
                    'AND tel_sessions_log.session_start_date < %s;',
                'client_phone':
                    'SELECT users.full_name, service_links.account_id, tel_numbers.tel_number '
                    'FROM tel_numbers, service_links, users '
                    'WHERE tel_numbers.slink_id = service_links.id '
                    'AND service_links.account_id = %s '
                    'AND users.id = service_links.user_id '
                    'AND tel_numbers.is_deleted = 0;'
            }  # Dict со строковыми предсатвлениями запросов к БД
            self.db_status = 'DISCONNECT'
            self.config = config
            self.db_name = self.config.get('DATABASE', 'DatabaseName')
            self.db_host = self.config.get('DATABASE', 'DatabaseHost')
            self.db_user = self.config.get('DATABASE', 'User')
            self.db_password = self.config.get('DATABASE', 'Password')
            self.mysql_connect = None
        except Exception as exc:
            print('ERROR: Ошибка конфигурации либо повреждены жизненно важные файлы приложения. '
                  'Дальнейшая работа невозможна Причина - %s. Проверьте журнал для получения информации.' % exc)

    def connect_to_db(self):  # Подключение к MySQL на сервере
        try:
            if self.db_status == 'DISCONNECT':
                self.mysql_connect = mysql.connector.connect(
                    user=self.db_user, password=self.db_password, host='localhost', database=self.db_name)
        except mysql.connector.Error as exc:
            self.db_status = 'ERROR'
            print('ERROR: Ошибка номер %s . Дальнейшая работа невозможна.'
                             'Проверьте журнал для получения информации.' % exc.errno)
        else:
            self.db_status = 'CONNECT'

    def disconnect_from_db(self):  # Отключение от MySQL на сервере
        try:
            if self.db_status == 'CONNECT':
                self.mysql_connect.close()
        except mysql.connector.Error as exc:
            self.db_status = 'ERROR'
            print('ERROR: Ошибка номер %s . Дальнейшая работа невозможна.'
                             'Проверьте журнал для получения информации.' % exc.errno)
        else:
            self.db_status = 'DISCONNECT'

    # Секция запрсов из БД

    def get_client_phone_number(self, account):  # Получить номер телефона абонента
        if self.db_status == 'DISCONNECT':
            self.connect_to_db()
        try:
            output = []
            client_query = self.queries['client_phone'] % account  # Селект на получение информации о номере клиента по ID
            cursor = self.mysql_connect.cursor()
            cursor.execute(client_query)
            for (full_name, account_id, tel_number) in cursor:
                output.append('%s|%s|%s' % \
                         (full_name, account_id, tel_number))

        except mysql.connector.Error as exc:
            print('ERROR: Ошибка MySQL %s. Дальнейшая работа невозможна. '
                             'Проверьте журнал для получения информации.' % exc.errno)
        else:
            self.disconnect_from_db()
            return output

    def get_client_info(self, account):  # Получить краткую информацию о клиенте
        if self.db_status == 'DISCONNECT':
            self.connect_to_db()
        try:
            output = ''
            client_query = self.queries['client-info-id'] % account  # Селект на получение информации о клиенте по ID
            cursor = self.mysql_connect.cursor()
            cursor.execute(client_query)
            for (account_id, login, full_name, actual_address, flat_number, comments, tariff_id) in cursor:
                output = '%s|%s|%s|%s|%s|%s|%s' % \
                         (account_id, login, full_name, actual_address, flat_number, comments, tariff_id)

        except mysql.connector.Error as exc:
            print('ERROR: Ошибка MySQL %s. Дальнейшая работа невозможна. '
                             'Проверьте журнал для получения информации.' % exc.errno)
        else:
            # self.disconnect_from_db()
            return output

    def get_clients_list(self):  # Получить список всех клиентов (физические и юридические лица)
        if self.db_status == 'DISCONNECT':
            self.connect_to_db()
        try:
            output = []
            client_query = self.queries['clients_list']# Селект на получение всех клиентов
            cursor = self.mysql_connect.cursor()
            cursor.execute(client_query)
            for (account_id, login, full_name, actual_address, flat_number, comments, tariff_id) in cursor:
                output.append('%s|%s|%s|%s|%s|%s|%s' % \
                         (account_id, login, full_name, actual_address, flat_number, comments, tariff_id))

        except mysql.connector.Error as exc:
            print('ERROR: Ошибка MySQL %s. Дальнейшая работа невозможна. '
                             'Проверьте журнал для получения информации.' % exc.errno)
        else:
            # self.disconnect_from_db()
            return output
        # return [
        #     '3548|net3514|Цедякова Наталья Александровна|ул. 3я Первомайская, д. 47|1||66',
        #     '3549|net3515|Цедякова Нина Викторовна|ул. Химиков, д. 5, кв 137|||66',
        #     '3550|net3516|Цедякова Рашидя Салитовна|ул. К.Либкнехта, д. 2, кв. 29|||66',
        #     '3551|net3517|Цедякова Татьяна Петровна|ул. Окт.революции, д. 35, кв. 33|||66',
        #     '3552|net3518|Цигуро Татьяна Николаевна|ул. Фр.Энгельса, д. 18, кв. 2|||66',
        #     '3553|net3519|Циркулева Вера Викторовна|ул. Урицкого, д. 60, кв. 9|||66',
        #     '3554|net3520|Чадин Дмитрий Михайлович|ул. Свердлова, д. 16, кв. 19|||66',
        #     '3645|net3609|ИП Шурупов В.В.|||GW#001630|65',
        #     '3646|net3611|ООО "АВК-ХИМ"|||GW#001631|65',
        #     '3655|net3613|ООО "Продукты деревни"|||GW #001640|65'
        # ]

    def get_all_client_calls(self, period, account):  # Список всех ЗМ, МН, МГ вызовов конкретного клиента
        if self.db_status == 'DISCONNECT':
            self.connect_to_db()
        try:
            last_day = calendar.monthrange(int(period[1]), int(period[0]))[1]  # Последний день периода
            start_period = datetime.datetime(int(period[1]), int(period[0]), 1, 00,
                                             00).timestamp() # unixtime объект первого числа периода
            end_period = datetime.datetime(int(period[1]), int(period[0]), last_day, 23, 59,
                                           59).timestamp()  # unixtime объект последнего числа периода
            output = []
            calls_query = self.queries['client-calls'] % \
                         (account, start_period, end_period)  # Селект на получение информации о клиенте по ID
            cursor = self.mysql_connect.cursor()
            cursor.execute(calls_query)
            for (Calling_Station_Id, Called_Station_Id, name, session_start_date,
                 duration, base_cost, sum_cost) in cursor:
                output.append('%s|%s|%s|%s|%s|%.2f|%.2f' %
                              (Calling_Station_Id, Called_Station_Id, name, session_start_date,
                               duration, base_cost, sum_cost))
        except mysql.connector.Error as exc:
            print('ERROR: Ошибка MySQL %s. Дальнейшая работа невозможна. '
                             'Проверьте журнал для получения информации.' % exc.errno)
        else:
            return output
        # return [
        #     '58122|84965404345|Стоимость: 2.5/1.5/1.5|1509516538|60|2.5|2.5',
        #     '58122|84965522777|Стоимость: 2.5/1.5/1.5|1509516577|300|2.5|12.5',
        #     '58148|84955038111|Стоимость: 2.5/1.5/1.5|1509520373|180|2.5|7.5',
        #     '58543|84952218761|Стоимость: 2.5/1.5/1.5|1509521483|60|2.5|2.5',
        #     '58148|84955038109|Стоимость: 2.5/1.5/1.5|1509521934|300|2.5|12.5',
        #     '58122|89263357484|Стоимость: 2.5/1.5/1.5|1509522430|60|2.5|2.5',
        #     '58148|84955038111|Стоимость: 2.5/1.5/1.5|1509523059|60|2.5|2.5',
        #     '58148|89160212145|Стоимость: 2/1.5/1.5|1509523059|60|2|2',
        #     '58148|84966474111|Стоимость: 1.5/1/1|1509523059|180|1.5|3',
        #     '58148|8103108437598|Стоимость: 12/11/10|1509523059|60|12|12'
        # ]

    def get_total_mg_summ(self,period, account):  # Считает сумму всех звонков (ЗН, МГ, МН) запросом total-mg-summ
        if self.db_status == 'DISCONNECT':
            self.connect_to_db()
        try:
            last_day = calendar.monthrange(int(period[1]), int(period[0]))[1]  # Последний день периода
            start_period = datetime.datetime(int(period[1]), int(period[0]), 1, 00,
                                             00).timestamp() # unixtime объект первого числа периода
            end_period = datetime.datetime(int(period[1]), int(period[0]), last_day, 23, 59,
                                           59).timestamp() # unixtime объект последнего числа периода
            output = ''
            summ_query = self.queries['mg-summ'] % \
                         (account, start_period, end_period)  # Селект на получение информации о клиенте по ID
            cursor = self.mysql_connect.cursor()
            cursor.execute(summ_query)
            for (total) in cursor:
                output = '%s' % total
        except mysql.connector.Error as exc:
            print('ERROR: Ошибка MySQL %s. Дальнейшая работа невозможна. '
                             'Проверьте журнал для получения информации.' % exc.errno)
        else:
            # self.disconnect_from_db()
            if output == 'None':
                return '0.00'
            else:
                return '%.2f' % float(output)

    # Генерирует dict о конкретном клиенте и полнымм набором данных для документов
    def get_stats_for_client(self, period, id_account):
        try:
            stats = {}
            client = self.get_client_info(id_account)

            if len(client) == 0:
                raise custom_exceptions.BadClientInfoExceprion

            info = client.split('|')  # Информация о клиенте
            account = info[0];login = info[1];name = info[2];address = info[3];flat = info[4]
            contract = info[5];tarif_id = info[6]
            calls = self.get_all_client_calls(period, account)
            if tarif_id == '66':
                rent_summ = '335.00'
            elif tarif_id == '65':
                rent_summ = '580.00'
            else:
                raise custom_exceptions.BadTarifException
            mg_summ = self.get_total_mg_summ(period, id_account)
            mg_summ_with_tax = '{0:.2f}'.format(float(mg_summ) * 1.18)
            total_summ = "{0:.2f}".format(float(rent_summ) + float(mg_summ))
            if not calls:
                calls = []
            stats[account] = [
                login, name, address, flat, contract, tarif_id, calls, rent_summ, mg_summ,
                mg_summ_with_tax, total_summ
            ]

        except custom_exceptions.BadClientInfoExceprion:
            print('ERROR: Невозможно получить данные о пользователе. Выполнение операции преврвано.')
        except custom_exceptions.BadTarifException:
            print('ERROR: Некорректный ID тарифа. Проврьте тарифный план клиента. Выполнение операции прервано.')
        except ValueError:
            print('ERROR: Некорректные значения суммы. Выполнение операции прервано.')
        except Exception:
            print('ERROR: Ошибка при работе с данными из БД. Проверьте журнал для получения информации.')
        else:
            print('COMPLITE: Данные о клиент успешно получены и обработаны')
            return stats

    def get_all_stats(self, period): # Генерирует dict со всеми клиентами и полным набором данных для документов
        try:
            stats = {}
            clients = self.get_clients_list() # !!! Список всех возможных клиентов
            if not clients:
                raise custom_exceptions.BadClientsListException

            for client in clients:
                info = client.split('|')

                account = info[0]; login = info[1]; name = info[2]; address = info[3]; flat = info[4]
                contract = info[5]; tarif_id = info[6]
                calls = self.get_all_client_calls(period, account)  # !!! Получаем список всех МГ, МН, ЗН соединений пользователя
                if tarif_id == '66':
                    rent_summ = '335.00'
                elif tarif_id == '65':
                    rent_summ = '580.00'
                else:
                    raise custom_exceptions.BadTarifException
                mg_summ = self.get_total_mg_summ(period, account)
                mg_summ_with_tax = '{0:.2f}'.format(float(mg_summ) * 1.18)
                total_summ = "{0:.2f}".format(float(rent_summ) + float(mg_summ))
                if not calls:
                    calls = []
                stats[account] = [
                    login, name, address, flat, contract, tarif_id, calls, rent_summ, mg_summ,
                    mg_summ_with_tax, total_summ
                ]
                print('INFO: Собрана статистика для %s' % account)
        except custom_exceptions.BadClientsListException:
            print('ERROR: Список пользователей пуст или несуществует. Выполнение операции преврвано.')
        except custom_exceptions.BadTarifException:
            print('ERROR: Некорректный ID тарифа. Проврьте тарифный план клиента. Выполнение операции прервано.')
        except ValueError:
            print('ERROR: Некорректные значения суммы. Выполнение операции прервано.')
        except Exception:
            print('ERROR: Ошибка при работе с данными из БД. Проверьте журнал для получения информации.')
        else:
            print('COMPLITE: Данные о клиентах успешно получены и обработаны')
            self.disconnect_from_db()
            return stats