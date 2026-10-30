from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Informações LivroTroca", {"fields": ("whatsapp", "localizacao")}),
        ("LGPD", {"fields": ("consentimento_lgpd", "data_consentimento")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Informações LivroTroca", {"fields": ("email", "whatsapp", "localizacao")}),
    )
    readonly_fields = ("consentimento_lgpd", "data_consentimento")
    list_display = ("username", "email", "whatsapp", "localizacao", "is_active")
    list_filter = UserAdmin.list_filter + ("localizacao",)


admin.site.register(Usuario, UsuarioAdmin)
