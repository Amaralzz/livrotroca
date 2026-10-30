from django import forms

from .models import Livro


class LivroForm(forms.ModelForm):
    """E2-01: cadastro de livro (título, autor, conservação e modalidade)."""

    class Meta:
        model = Livro
        fields = ("titulo", "autor", "conservacao", "modalidade")
        widgets = {
            "titulo": forms.TextInput(attrs={"placeholder": "Ex.: Grande Sertão: Veredas"}),
            "autor": forms.TextInput(attrs={"placeholder": "Ex.: Guimarães Rosa"}),
            "conservacao": forms.RadioSelect,
            "modalidade": forms.RadioSelect,
        }
        help_texts = {
            "modalidade": "Empréstimo: prazo de 14 dias. Doação: entrega definitiva.",
        }
