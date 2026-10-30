from django.contrib import admin

from .models import Livro


@admin.register(Livro)
class LivroAdmin(admin.ModelAdmin):
    list_display = ("titulo", "autor", "dono", "modalidade", "status", "criado_em")
    list_filter = ("modalidade", "status", "conservacao")
    search_fields = ("titulo", "autor", "dono__username")
