from django.utils import timezone
from babel.dates import format_datetime


RU_LOCALE = "ru"           # «ru_RU» тоже подойдёт
FMT = "d MMMM y  в  HH:mm"   # «27 апреля 2025 17:00»

def ru_dt(dt):
    """
    Local-time → человеко-читаемая дата/время по-русски.
    """
    if not dt:
        return "—"
    aware = timezone.localtime(dt)          # учитываем TZ Django
    return format_datetime(aware, FMT, locale=RU_LOCALE)