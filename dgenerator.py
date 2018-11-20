#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" DGenerator цикл main """

import cli

if __name__ == "__main__":
    command_promt = cli.CommandPrompt()
    try:
        command_promt.cmdloop()

    except KeyboardInterrupt:
        command_promt.end_work()
        print('Завершение сеанса. До скорой встречи.')
