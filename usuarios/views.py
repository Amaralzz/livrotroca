from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from .forms import ReenvioConfirmacaoForm, RegistroForm
from .tokens import gerador_token_ativacao

User = get_user_model()


def criar_usuario(request):
    """E1-01: cadastro. A conta nasce inativa e recebe o link de confirmação."""
    if request.user.is_authenticated:
        return redirect("catalogo:busca")
    if request.method == "POST":
        form = RegistroForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            enviar_email_confirmacao(request, usuario)
            request.session["email_pendente"] = usuario.email
            return redirect("confirme_email")
    else:
        form = RegistroForm()
    return render(request, "usuarios/registro.html", {"form": form})


def enviar_email_confirmacao(request, usuario):
    uid = urlsafe_base64_encode(force_bytes(usuario.pk))
    token = gerador_token_ativacao.make_token(usuario)
    link = request.build_absolute_uri(reverse("ativar_conta", args=[uid, token]))
    contexto = {"usuario": usuario, "link": link}

    send_mail(
        subject="Confirme sua conta no LivroTroca",
        message=render_to_string("usuarios/email_confirmacao.txt", contexto),
        html_message=render_to_string("usuarios/email_confirmacao.html", contexto),
        from_email=None,
        recipient_list=[usuario.email],
    )


def confirme_email(request):
    """E1-02: aviso para confirmar o e-mail, com opção de reenviar o link."""
    form = ReenvioConfirmacaoForm(
        request.POST or None,
        initial={"email": request.session.get("email_pendente", "")},
    )
    if request.method == "POST" and form.is_valid():
        usuario = User.objects.filter(
            email__iexact=form.cleaned_data["email"], is_active=False
        ).first()
        if usuario:
            enviar_email_confirmacao(request, usuario)
        # Mensagem genérica: não revela se o e-mail está cadastrado
        messages.info(
            request,
            "Se houver uma conta aguardando confirmação com este e-mail, "
            "enviamos um novo link.",
        )
        return redirect("confirme_email")
    return render(request, "usuarios/confirme_email.html", {"form": form})


def ativar_conta(request, uidb64, token):
    """E1-02: ativa a conta pelo link recebido por e-mail."""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        usuario = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        usuario = None

    if usuario is not None and gerador_token_ativacao.check_token(usuario, token):
        usuario.is_active = True
        usuario.save(update_fields=["is_active"])
        return render(request, "usuarios/ativacao_sucesso.html")

    return render(request, "usuarios/ativacao_invalida.html", status=400)

