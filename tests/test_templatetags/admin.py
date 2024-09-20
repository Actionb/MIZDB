from django.contrib import admin

from .models import Foo

admin_site = admin.AdminSite(name="test_templatetags")


@admin.register(Foo, site=admin_site)
class FooAdmin(admin.ModelAdmin):
    pass
