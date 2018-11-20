# -*- coding: utf-8 -*-

""" Поиск клиента из списка пользователей БД и отображение в cli """

from terminaltables import AsciiTable

class Finder:
    def __init__(self, utm_data_object):
        self.utm_data = utm_data_object

    def find_user(self, name):
        try:
            all_users_list = self.utm_data.get_clients_list()
            all_data = []
            header = [['ID Аккаунта', 'Логин', 'ФИО', 'Адрес', 'Квартира', 'Номер договора (комментарий)', 'ID тарифа']]
            found_clients = [c.split('|') for c in all_users_list if name in c]
            if not found_clients:
                print('NOT FOUND: Клиент с указанным именем не найден в базе данных')
                return
            else:
                all_data = header + found_clients
            view = AsciiTable(all_data)
            print(view.table)
        except Exception as exc:
            print('ERROR: Невозможно выпонить поиск килента. причина - %s. '
                  'Проверьте журнал для получения информации.' % exc)