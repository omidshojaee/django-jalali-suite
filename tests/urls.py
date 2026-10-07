from django.contrib import admin
from django.urls import path

from tests.testapp import hierarchy

urlpatterns = [
    path("admin/", admin.site.urls),
    path("hier/", hierarchy.site.urls),
    path("bare/", hierarchy.bare_site.urls),
]
