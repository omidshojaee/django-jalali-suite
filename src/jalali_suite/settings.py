from django.conf import settings
from django.core.signals import setting_changed

DEFAULTS = {
    "DIGITS": "latin",
    "DATE_FORMAT": "%Y/%m/%d",
    "DATETIME_FORMAT": "%Y/%m/%d %H:%M:%S",
    "ADMIN_AUTO_CONVERT_LIST_DISPLAY": False,
}


class SuiteSettings:
    @property
    def user_settings(self):
        if not settings.configured:
            return {}
        return getattr(settings, "JALALI_SUITE", {})

    def get(self, name):
        if name not in DEFAULTS:
            raise AttributeError(f"Invalid Jalali Suite setting: {name}")
        return self.user_settings.get(name, DEFAULTS[name])

    def reload(self):
        pass


jalali_settings = SuiteSettings()


def reload_settings(*, setting, **kwargs):
    if setting == "JALALI_SUITE":
        jalali_settings.reload()


setting_changed.connect(reload_settings)
