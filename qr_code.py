# -*- coding: utf-8 -*-

""" Генератор QR кодов для Сбербанка  """

import qrcode
from os import path, makedirs

class QR_generator():
    def __init__(self, filname, user_data, path):
        self.user_data = user_data
        self.bills_and_qr_dir = path
        self.filename = filname

    def generate_qr_code(self):
        try:
            qr_file_path = path.join(self.bills_and_qr_dir, '%s.png' % (self.filename))
            image_tag = '<img src="%s.png" width="150px"/>' % (
            self.filename)  # Вернуть этот тэг с путем для шаблонизатора

            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=3,
                border=1,
            )
            qr.add_data(self.user_data)
            qr.make(fit=True)

            qr_img = qr.make_image()
            qr_img.save(qr_file_path)

            return image_tag
        except Exception:
            return 'ERROR'

