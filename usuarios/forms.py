from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, UsernameField
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from .backends import buscar_por_usuario_ou_email
from .models import Usuario


class RegistroForm(UserCreationForm):
    """Cadastro de membro (E1-01 / RF01)."""

    consentimento_lgpd = forms.BooleanField(
        required=True,
        label=(
            "Li e concordo com a Política de Privacidade e autorizo o uso dos meus "
            "dados para o funcionamento do LivroTroca."
        ),
        error_messages={
            "required": "É preciso aceitar a Política de Privacidade para criar a conta."
        },
    )

    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = ("username", "email", "whatsapp", "localizacao")
        labels = {"whatsapp": "WhatsApp", "localizacao": "Campus ou bairro"}

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if Usuario.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Já existe uma conta com este e-mail.")
        return email

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.is_active = False  # só ativa após confirmar o e-mail (E1-02)
        usuario.consentimento_lgpd = True
        usuario.data_consentimento = timezone.now()
        if commit:
            usuario.save()
            self.save_m2m()
        return usuario


class ReenvioConfirmacaoForm(forms.Form):
    email = forms.EmailField(label="E-mail cadastrado")


class EntrarForm(AuthenticationForm):
    """E1-03: login por usuário ou e-mail, com mensagens que não expõem dados."""

    username = UsernameField(
        label="Usuário ou e-mail",
        widget=forms.TextInput(attrs={"autofocus": True, "autocomplete": "username"}),
    )
    error_messages = {
        "invalid_login": "Usuário/e-mail ou senha incorretos.",
        "inactive": "Sua conta ainda não foi ativada.",
    }

    def clean(self):
        identificador = self.cleaned_data.get("username")
        senha = self.cleaned_data.get("password")
        if identificador and senha:
            usuario = buscar_por_usuario_ou_email(identificador)
            # Só avisa sobre a ativação pendente quando a senha está correta
            if usuario and not usuario.is_active and usuario.check_password(senha):
                raise forms.ValidationError(
                    format_html(
                        'Sua conta ainda não foi ativada. Confirme seu e-mail ou '
                        '<a href="{}">peça um novo link</a>.',
                        reverse("confirme_email"),
                    ),
                    code="inactive",
                )
        return super().clean()
