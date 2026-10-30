from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views
from .forms import EntrarForm

urlpatterns = [
    # E1-01 e E1-02
    path("criar/", views.criar_usuario, name="criar_usuario"),
    path("confirme-email/", views.confirme_email, name="confirme_email"),
    path("ativar/<uidb64>/<token>/", views.ativar_conta, name="ativar_conta"),
    # E1-03
    path(
        "entrar/",
        auth_views.LoginView.as_view(
            template_name="usuarios/entrar.html",
            authentication_form=EntrarForm,
            redirect_authenticated_user=True,
        ),
        name="entrar",
    ),
    path("sair/", auth_views.LogoutView.as_view(), name="sair"),
    # E1-05
    path(
        "senha/recuperar/",
        auth_views.PasswordResetView.as_view(
            template_name="usuarios/senha_recuperar.html",
            email_template_name="usuarios/email_redefinir_senha.txt",
            subject_template_name="usuarios/email_redefinir_senha_assunto.txt",
            success_url=reverse_lazy("senha_enviada"),
        ),
        name="senha_recuperar",
    ),
    path(
        "senha/enviada/",
        auth_views.PasswordResetDoneView.as_view(template_name="usuarios/senha_enviada.html"),
        name="senha_enviada",
    ),
    path(
        "senha/nova/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="usuarios/senha_nova.html",
            success_url=reverse_lazy("senha_alterada"),
        ),
        name="senha_nova",
    ),
    path(
        "senha/alterada/",
        auth_views.PasswordResetCompleteView.as_view(template_name="usuarios/senha_alterada.html"),
        name="senha_alterada",
    ),
]
