# -*- coding: utf-8 -*-

""" Управление конфигурацией приложения """

import configparser
from os import path

class ConfigHandler():

    def __init__(self):
        try:
            self.app_dir = path.dirname(path.realpath(__file__))
            self.config_path = '%s/config/dgenerator.conf' % self.app_dir
            self.config = configparser.ConfigParser()
            self.config.read(self.config_path)
        except Exception as exc:
            print('ERROR: Невозможно получить конфигурацию. Причина - %s. '
                  'Проверьте журнал для получения информации.' % exc)

    def get_config(self):
        return self.config

    def view_config(self):
        for c in open(self.config_path, 'r'): print(c, end='')

    def save_config(self):
        with open(self.config_path, "w") as config_file:
            self.config.write(config_file)