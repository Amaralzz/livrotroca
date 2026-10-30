from django.contrib import admin

from .models import Emprestimo


@admin.register(Emprestimo)
class EmprestimoAdmin(admin.ModelAdmin):
    list_display = ("livro", "solicitante", "modalidade", "status", "criado_em", "data_limite")
    list_filter = ("modalidade", "status")
    search_fields = ("livro__titulo", "solicitante__username", "livro__dono__username")
