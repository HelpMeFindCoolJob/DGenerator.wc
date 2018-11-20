# -*- coding: utf-8 -*-

""" CLI module """

import cmd
import period
import cdr
import utm_connect
import config_handler
import generate_docs
import find_users
import utm_data
import os
import call_stat
import locale

class CommandPrompt(cmd.Cmd):
    def __init__(self):
        cmd.Cmd.__init__(self)
        self.config_manager = config_handler.ConfigHandler()
        self.config = self.config_manager.get_config()
        self.per = period.Period()
        self.connection = utm_connect.ServerConnect(self.config)
        self.prompt = 'Period (%s %s) Connect (%s) >>> ' % (self.per.get_period()[0],
                                                            self.per.get_period()[1], self.connection.get_status())
        self.intro = 'Вас приветствует DGenerator. Для получения справки введите ? или воспользуйтесь командой help'
        self.doc_header = 'Доступные команды (для справки по конкретной команде наберите "help <Команда>")'

        locale.setlocale(locale.LC_ALL, 'Russian_Russia.1251')

    def default(self, line):
        print('Некорректная команда. Воспользутесь командой help или ? для получения помощи.')

    def emptyline(self):
        pass

    def change_promt(self, new_promt):
        self.prompt = new_promt

    def end_work(self):
        if self.connection.get_status() == 'YES':
            self.connection.disconnect()

    # Секция для команд, обеспечивающих генерирование документов
    def do_bill(self, args):
        """Позволяет запустить процесс генерирования телефонного счета указанному в качестве параметра клиенту.
        В качестве параметра допускается передавать ID Аккаунта в формате <ID Аккаунта>. Отсутсвие параметров не
        допускается. Например, команда bill 3354 запустит процесс генерирования счета для клиента с ID аккаунта 3354.
        Обязательно обращайте внимание на отчетный период (строка состояния данного приложения).
        Директорию, в которой хранятся файлы счетов можно узнать в соотвествующей секции конфигурации
        (которую можно просмотреть командой config)."""

        arguments = [a if not a.isdigit() else int(a) for a in args.split()]

        if self.connection.get_status() == 'YES':
            if len(arguments) == 1 and arguments[0] in range(1, 9999):
                docs_generator = generate_docs.DocsGenerator(self.per.get_period(), self.config)
                docs_generator.generate_bill_for_client(str(arguments[0]))
            else:
                print('Некорректные параметры. Воспользутесь командой help generate_client_bill для получения помощи.')
        else:
            print('Проблемы с подключением к серверу. Воспользутесь командой connect для подключения или командой '
                  'help bill для получения помощи.')

    def do_detail(self, args):
        """Позволяет запустить процесс генерирования детализации телефонных соединений указанному в качестве параметра
        клиенту. В качестве параметра допускается передавать ID Аккаунта <ID Аккаунта>. Отсутсвие параметров не
        допускается. Например, команда detail 3354 запустит процесс генерирования счета для клиента с ID аккаунта
        3354. Обязательно обращайте внимание на отчетный период (строка состояния данного приложения). Директорию,
        в которой хранятся файлы счетов можно узнать в соотвествующей секции конфигурации (которую можно просмотреть
        командой config)."""

        arguments = [a if not a.isdigit() else int(a) for a in args.split()]

        if self.connection.get_status() == 'YES':
            if len(arguments) == 1 and arguments[0] in range(1, 9999):  # Аккаунт
                docs_generator = generate_docs.DocsGenerator(self.per.get_period(), self.config)
                docs_generator.generate_detail_for_client(str(arguments[0]))
            else:
                print('Некорректные параметры. Воспользутесь командой help detail для получения помощи.')
        else:
            print('Проблемы с подключением к серверу. Воспользутесь командой connect для подключения или командой '
                  'help reports для получения помощи.')

    def do_reports(self, args):
        """Позвлояет запустить процесс генерирования отчетных документов для финансового отдела. Данная команда
        не предусматривает использования параметров. Директорию, в которой хранятся файлы отчетов можно узнать в
        соотвествующей секции конфигурации (которую можно просмотреть командой show_config)."""

        arguments = [int(a) for a in args.split() if a.isdigit()]

        if self.connection.get_status() == 'YES':
            if len(arguments) == 1 and arguments[0] in range(1, 999999):
                docs_generator = generate_docs.DocsGenerator(self.per.get_period(),
                                                             self.config, start_bill_number=arguments[0])
                docs_generator.generate_reports()
                self.config_manager.save_config()  # Сохраняем файл конфига для сохарнения номера счета для 1С
            elif not args:
                docs_generator = generate_docs.DocsGenerator(self.per.get_period(), self.config)
                docs_generator.generate_reports()
                self.config_manager.save_config()  # Сохраняем файл конфига для сохарнения номера счета для 1С
            else:
                print('Некорректные параметры. Воспользутесь командой '
                      'help reports для получения помощи для подключения')
        else:
            print('Проблемы с подключением к серверу. Воспользутесь командой connect для подключения или командой '
                  'help details для получения помощи.')

    def do_details(self, args):
        """Позволяет запустить процесс генерирования детализаций для всех клиентов (физических и юридических лиц)
        Обязательно обращайте внимание на отчетный период. Директорию, в которой хранятся файлы
        счетов можно узнать в соотвествующей секции конфигурации (которую можно просмотреть командой show_config).
        Данная команда не предусматривает использования параметров."""

        if not args:
            if self.connection.get_status() == 'YES':
                docs_generator = generate_docs.DocsGenerator(self.per.get_period(), self.config)
                docs_generator.generate_details()
            else:
                print('Проблемы с подключением к серверу. Воспользутесь командой connect для подключения или командой '
                      'help details для получения помощи.')
        else:
            print('Некорректные параметры. Воспользутесь командой help details для получения помощи для подключения')

    def do_bills(self, args):
        """Позволяет запустить процесс генерирования квитанций для всех клиентов физических лиц.
        Обязательно обращайте внимание на отчетный период. Директорию, в которой хранятся файлы
        счетов можно узнать в соотвествующей секции конфигурации (которую можно просмотреть командой show_config).
        Данная команда не предусматривает использования параметров."""

        if not args:
            if self.connection.get_status() == 'YES':
                docs_generator = generate_docs.DocsGenerator(self.per.get_period(), self.config)
                docs_generator.generate_bills()
            else:
                print('Проблемы с подключением к серверу. Воспользутесь командой connect для подключения или командой '
                      'help bills для получения помощи.')
        else:
            print('Некорректные параметры. Воспользутесь командой help bills для получения помощи для подключения')

    def do_cdr(self, args):
        """Позволяет производить действия с CDR записями о вызовах, такие как - преобразование файлов в формат UTM5,
        передача конвертированных файлов на сервер UTM5, а также запуск UTM5 CDR парсера на сервере с отчетом о выполнении.
        В качестве параметров допускается передавать режим обработки CDR записей в формате <Режим>.
        Допускаются следующие параметры: cnv, который указывает необходимость только сконфертировать CDR-ы в формат UTM5,
        параметр trn, который указывает приложению сконвертировать CDR-ы в формат UTM5 и после этого отправить уже
        сконвертированные файлы на сервер, при помощи scp(требуется активное ssh подключение к серверу),
        а параметр prs, позволяет указать на необходимость запуска UTM5 парсера отправленных и сконвертированных
        CDR файлов на сервере (требуется активное ssh подключение) Отсуствие параметров не допускается.
        Например, команда cdr cnv только сконвертирвует CDR-ы, cdr trn сконвертирует и отправит на сервер UTM5, а
        cdr prs сокнвертирует, отправит на сервер и запустит utm5_send_cdr для файлов, которые вы укажите."""

        argument = [a for a in args.split() if a.isalpha()]

        if len(argument) == 1:
            if argument[0] == 'cnv':
                cdr_worker = cdr.Cdr(self.per.get_period(), self.config)
                cdr_worker.convert()
            elif argument[0] == 'trn' and self.connection.get_status() == 'YES':
                cdr_worker = cdr.Cdr(self.per.get_period(), self.config, self.connection)
                cdr_worker.transfer()
            elif argument[0] == 'prs' and self.connection.get_status() == 'YES':
                cdr_worker = cdr.Cdr(self.per.get_period(), self.config, self.connection)
                cdr_worker.parse()
            else:
                print('Некорректные параметры или проблемы с подключением к серверу. '
                      'Воспользутесь командой help cdr для получения помощи.')
        else:
            print('Некорректные параметры. Воспользутесь командой help cdr для получения помощи.')

    # Секция для команд, предоставляющих сервисные услуги
    def do_connect(self, args):
        """Позволяет запустить процесс установления связи с помощью ssh туннеля с сервером utm5 с пробросом порта для mysql.
        Текущий статус соелинения вы можете увидеть слева от курсора ввода команд в поле Connect(<status>). Данная команда
        не предусматривает использование параметров."""

        if not args:
            if self.connection.get_status() == 'NO':
                self.connection.connect()
                self.change_promt('Period (%s %s) Connect (%s) >>> ' % (self.per.get_period()[0],
                                                                        self.per.get_period()[1],
                                                                        self.connection.get_status()))
            else:
                print(
                    'Соединение уже установлено. Если вы хотите переподключиться, сначала используйте команду disconnect,'
                    'после чего повторите ввод данной команды.')
        else:
            print('Некорректные параметры. Воспользутесь командой help connect для получения помощи.')

    def do_disconnect(self, args):
        """Позволяет запустить процесс закрытия всех подключений к серверу utm5 и закрытию ssh туннеля.
         Текущий статус соелинения вы можете увидеть слева от курсора ввода команд в поле Connect(<status>).
         Данная команда не предусматривает использование параметров."""

        if not args:
            if self.connection.get_status() == 'YES':
                self.connection.disconnect()
                self.change_promt('Period (%s %s) Connect (%s) >>> ' % (self.per.get_period()[0],
                                                                        self.per.get_period()[1],
                                                                        self.connection.get_status()))
            else:
                print('Соединение уже разорвано. Если вы хотите подключиться к серверу, воспользуйтесь командой connect')
        else:
            print('Некорректные параметры. Воспользутесь командой help disconnect для получения помощи.')

    def do_period(self, args):
        """Позволяет установить отчетный период. В качестве параметра допускается передавать месяц и год
        в формате <Месяц Год>. Отсуствие параметров не допускается Например, команда period 7 2017 установит в
        качестве отчетного периода текущего сеанса отрезок времени от
        01.07.2017 0:00 до 30.07.2017 23:59 включительно."""

        arguments = [int(a) for a in args.split() if a.isdigit()]

        if len(arguments) == 2 and arguments[0] in range(1, 13) and arguments[1] in range(2010, 2100):
            self.per.set_period(arguments)
            self.change_promt('Period (%s %s) Connect (%s) >>> ' % (self.per.get_period()[0],
                                                      self.per.get_period()[1], self.connection.get_status()))
        else:
            print('Некорректные параметры. Воспользутесь командой help period для получения помощи.')

    def do_config(self, args):
        """Отображает текущую конфигурацию сеанса. Данная команда не предусматривает использования параметров."""

        if not args:
            self.config_manager.view_config()
        else:
            print('Некорректные параметры. Воспользутесь командой help show_config для получения помощи.')

    def do_log(self, args):
        """Отображает последние записи журнала. Данная команда не предусматривает использования параметров."""

        if not args:
            pass
        else:
            print('Некорректные параметры. Воспользутесь командой help log для получения помощи.')

    def do_clear(self, args):
        """С помощью данной команды вы можеет очистить экран терминала. Данная команда не предусматривает
         наличия параметров."""

        if not args:
            os.system('cls' if os.name == 'nt' else 'clear')
        else:
            print('Некорректные параметры. Воспользутесь командой help clear для получения помощи.')

    def do_find(self, args):
        """Позволяет осуществлять поиск и выввод информации о клиентах в терминал. В качестве параметра допускается
        передавать ФИО полностью через пробел либо комбинацию имени или фамилии-имени клиента в форматах -
        <Фамилия Имя Отчество> для поиска по полному ФИО, <Фамилия Имя> для поиска по фамилии-имени либо
        <Фамилия/Имя/Отчество> для поиска по одному из параметров. Отсуствие параметров не допускается. Регистр не
        имеет значения. Например, команда find Синий Иван Семенович произведет поиск клиента с указанными в параметрах
        ФИО, find ГОЛУБОЙ сЕМЕен попробует найти информацию о клиенте с указанной комбинацией фамилии и имени.
        А find степен найдет всех клиентов с именем Степан."""

        arguments = [a.lower() for a in args.split()]

        if self.connection.get_status() == 'YES':
            data_worker = utm_data.Data(self.config)
            finder = find_users.Finder(data_worker)
            if len(arguments) == 1 and arguments[0].isalpha():
                finder.find_user(args.title())
            elif len(arguments) == 2 and arguments[0].isalpha() and arguments[1].isalpha():
                finder.find_user(args.title())
            elif len(arguments) == 3 and arguments[0].isalpha() and arguments[1].isalpha() and arguments[2].isalpha():
                finder.find_user(args.title())
            else:
                print('Некорректные параметры. Воспользутесь командой help find для получения помощи.')
        else:
            print('Проблемы с подключением к серверу. Воспользутесь командой connect для подключения или командой '
                  'help find для получения помощи.')

    def do_stat(self, args):
        """Позволяет сгенерировать полную детализацию всех успешных вызовов для конкретного клиента и/или полную
         статистику использвания транков/опреаторов. В качестве парамаетра допускается передавать ID аккаунта
         клиента либо параметр <trunks>. Команда stat 12 запустить процесс генерирования полной детализации для
         клиента с ID аккаунта 12. Команда stat trunks запускает процесс генерирования статистики использования
         транков. Отсутствие параметров не допускается."""

        arguments = [a for a in args.split()]
        if self.connection.get_status() == 'YES':
            if len(arguments) == 1 and arguments[0].isdigit() and int(arguments[0]) in range(1, 9999):
                stat_obj = call_stat.StatWorker(self.config, self.per.get_period())
                stat_obj.get_client_stat(args)
            elif len(arguments) == 1 and arguments[0] == 'trunks':
                stat_obj = call_stat.StatWorker(self.config, self.per.get_period())
                stat_obj.get_trunks_stat()
            else:
                print('Некорректные параметры. Воспользутесь командой help stat для получения помощи.')
        else:
            print('Проблемы с подключением к серверу. Воспользутесь командой connect для подключения или командой '
                  'help stat для получения помощи.')

    def do_exit(self, arg):
        """Обеспечивает выход из приложения."""

        print('Завершение сеанса. До скорой встречи.')
        self.end_work()
        return True