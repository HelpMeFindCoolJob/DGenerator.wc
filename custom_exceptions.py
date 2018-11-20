# -*- coding: utf-8 -*-

""" Пользовательские исключения """

class NoUploadDirException(Exception):
    pass

class BadStatsException(Exception):
    pass

class NotTemplateFileException(Exception):
    pass

class BadQrException(Exception):
    pass

class NotReasonGenerateDetailExceprion(Exception):
    pass

class BadClientsListException(Exception):
    pass

class BadClientInfoExceprion(Exception):
    pass

class BadTarifException(Exception):
    pass