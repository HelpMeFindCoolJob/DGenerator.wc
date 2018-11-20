# -*- coding: utf-8 -*-

""" Управление "отчетным периодом" для финансовых документов """

import datetime

class Period:

    def __init__(self):
        self.month = datetime.datetime.now().month - 1
        self.year = datetime.datetime.now().year

    def get_period(self):
        return [str(self.month), str(self.year)] if self.month != 0 else [str(12), str(self.year-1)]

    def set_period(self, new_period):
        self.month = new_period[0]
        self.year = new_period[1]
        print('Отчетный период %s %s установлен в качестве текущего' % (self.month, self.year))