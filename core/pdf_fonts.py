import os
from django.conf import settings
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT_PATH = os.path.join(settings.BASE_DIR, 'fonts', 'DejaVuSans.ttf')

def register_dejavu():
    if 'DejaVu' not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont('DejaVu', FONT_PATH))
