from django.apps import AppConfig
from django.core import checks


class JalaliSuiteConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "jalali_suite"
    verbose_name = "Jalali Suite"

    def ready(self):
        checks.register(check_date_hierarchy, checks.Tags.admin)


def check_date_hierarchy(app_configs=None, **kwargs):
    """Warn when ``date_hierarchy`` would drill down by the Gregorian calendar."""
    from django.contrib.admin.sites import all_sites
    from django.core.exceptions import FieldDoesNotExist

    from .admin import JalaliDateAdminMixin
    from .models import JalaliDateField, JalaliDateTimeField

    warnings = []
    for site in all_sites:
        for model, model_admin in site._registry.items():
            name = getattr(model_admin, "date_hierarchy", None)
            if not isinstance(name, str) or "__" in name:
                continue
            try:
                field = model._meta.get_field(name)
            except FieldDoesNotExist:
                continue
            if not isinstance(field, (JalaliDateField, JalaliDateTimeField)):
                continue
            handled = isinstance(model_admin, JalaliDateAdminMixin) and model_admin.jalali_date_hierarchy
            if not handled:
                warnings.append(
                    checks.Warning(
                        f"date_hierarchy = {name!r} is a Jalali field, but Django's "
                        "drill-down uses the Gregorian calendar and would filter the "
                        "wrong dates.",
                        hint="Use JalaliDateAdminMixin (or JalaliDateModelAdmin) with "
                        "jalali_date_hierarchy = True.",
                        obj=model_admin.__class__,
                        id="jalali_suite.W001",
                    )
                )
    return warnings
