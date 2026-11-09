from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from emprestimos.tasks import verificar_agendador

from .tokens import gerador_token_ativacao

User = get_user_model()
SENHA = "SenhaForte#2026"


def criar(username="ana", ativo=True):
    return User.objects.create_user(
        username=username, email=f"{username}@unimontes.br", password=SENHA,
        whatsapp="38999990000", localizacao="campus_1", is_active=ativo,
    )


class LoginLogoutTests(TestCase):
    """E1-03 · Fazer login e logout."""

    def setUp(self):
        self.usuario = criar()

    def test_login_com_nome_de_usuario(self):
        resposta = self.client.post(reverse("entrar"), {"username": "ana", "password": SENHA})
        self.assertRedirects(resposta, reverse("catalogo:busca"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.usuario.pk)

    def test_login_com_email(self):
        resposta = self.client.post(reverse("entrar"), {"username": "ANA@unimontes.br", "password": SENHA})
        self.assertRedirects(resposta, reverse("catalogo:busca"))

    def test_erro_generico_nao_revela_se_a_conta_existe(self):
        senha_errada = self.client.post(reverse("entrar"), {"username": "ana", "password": "errada"})
        inexistente = self.client.post(reverse("entrar"), {"username": "ninguem", "password": "errada"})
        self.assertContains(senha_errada, "Usuário/e-mail ou senha incorretos.")
        self.assertContains(inexistente, "Usuário/e-mail ou senha incorretos.")

    def test_conta_inativa_avisa_sobre_confirmacao(self):
        criar("bia", ativo=False)
        resposta = self.client.post(reverse("entrar"), {"username": "bia", "password": SENHA})
        self.assertContains(resposta, "ainda não foi ativada")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout(self):
        self.client.force_login(self.usuario)
        resposta = self.client.post(reverse("sair"))
        self.assertRedirects(resposta, reverse("catalogo:busca"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_paginas_restritas_exigem_login(self):
        resposta = self.client.get(reverse("catalogo:meus"))
        self.assertRedirects(resposta, reverse("entrar") + "?next=" + reverse("catalogo:meus"))


class RecuperacaoSenhaTests(TestCase):
    """E1-05 · Recuperar senha por e-mail."""

    def setUp(self):
        self.usuario = criar()

    def pedir_link(self):
        self.client.post(reverse("senha_recuperar"), {"email": "ana@unimontes.br"})
        self.assertEqual(len(mail.outbox), 1)
        corpo = mail.outbox[0].body
        return corpo[corpo.index("http://testserver") + len("http://testserver"):].split()[0]

    def test_envia_link_e_permite_nova_senha(self):
        link = self.pedir_link()
        resposta = self.client.get(link, follow=True)
        self.assertTrue(resposta.context["validlink"])
        self.client.post(resposta.redirect_chain[-1][0], {
            "new_password1": "OutraSenha#2026", "new_password2": "OutraSenha#2026",
        })
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password("OutraSenha#2026"))

    def test_link_de_uso_unico(self):
        link = self.pedir_link()
        resposta = self.client.get(link, follow=True)
        self.client.post(resposta.redirect_chain[-1][0], {
            "new_password1": "OutraSenha#2026", "new_password2": "OutraSenha#2026",
        })
        self.client.logout()
        segunda = self.client.get(link, follow=True)
        self.assertFalse(segunda.context["validlink"])

    def test_link_expira_em_30_minutos(self):
        link = self.pedir_link()
        agora = PasswordResetTokenGenerator()._now()
        with mock.patch.object(PasswordResetTokenGenerator, "_now", return_value=agora + timedelta(minutes=31)):
            resposta = self.client.get(link, follow=True)
        self.assertFalse(resposta.context["validlink"])

    def test_email_desconhecido_nao_e_revelado(self):
        resposta = self.client.post(reverse("senha_recuperar"), {"email": "ninguem@unimontes.br"})
        self.assertRedirects(resposta, reverse("senha_enviada"))
        self.assertEqual(len(mail.outbox), 0)

    def test_link_de_ativacao_nao_usa_o_prazo_de_30_minutos(self):
        pendente = criar("caio", ativo=False)
        uid = urlsafe_base64_encode(force_bytes(pendente.pk))
        token = gerador_token_ativacao.make_token(pendente)
        agora = gerador_token_ativacao._now()
        with mock.patch.object(type(gerador_token_ativacao), "_now", return_value=agora + timedelta(hours=2)):
            resposta = self.client.get(reverse("ativar_conta", args=[uid, token]))
        self.assertEqual(resposta.status_code, 200)


class InfraestruturaTests(TestCase):
    """E8-02 · Celery + Celery Beat e SMTP."""

    def test_tarefa_de_teste_do_agendador(self):
        self.assertTrue(verificar_agendador.apply().get())

    def test_agendamento_configurado(self):
        from django.conf import settings
        tarefas = [t["task"] for t in settings.CELERY_BEAT_SCHEDULE.values()]
        self.assertIn("emprestimos.tasks.verificar_agendador", tarefas)
