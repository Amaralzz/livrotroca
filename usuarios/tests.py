from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .tokens import gerador_token_ativacao

User = get_user_model()

DADOS = {
    "username": "maria",
    "email": "maria@unimontes.br",
    "whatsapp": "38999990000",
    "localizacao": "campus_1",
    "password1": "SenhaForte#2026",
    "password2": "SenhaForte#2026",
    "consentimento_lgpd": "on",
}


def link_ativacao(usuario):
    uid = urlsafe_base64_encode(force_bytes(usuario.pk))
    token = gerador_token_ativacao.make_token(usuario)
    return reverse("ativar_conta", args=[uid, token])


class CadastroTests(TestCase):
    """E1-01 · Cadastrar conta com contato e localização."""

    def test_cadastro_cria_conta_inativa_e_envia_email(self):
        resposta = self.client.post(reverse("criar_usuario"), DADOS)
        self.assertRedirects(resposta, reverse("confirme_email"))
        usuario = User.objects.get(username="maria")
        self.assertFalse(usuario.is_active)
        self.assertEqual(usuario.whatsapp, "38999990000")
        self.assertEqual(usuario.localizacao, "campus_1")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/usuarios/ativar/", mail.outbox[0].body)

    def test_senha_guardada_com_argon2(self):
        self.client.post(reverse("criar_usuario"), DADOS)
        self.assertTrue(User.objects.get(username="maria").password.startswith("argon2"))

    def test_consentimento_lgpd_obrigatorio_e_registrado(self):
        sem_consentimento = {k: v for k, v in DADOS.items() if k != "consentimento_lgpd"}
        self.client.post(reverse("criar_usuario"), sem_consentimento)
        self.assertFalse(User.objects.exists())

        self.client.post(reverse("criar_usuario"), DADOS)
        usuario = User.objects.get(username="maria")
        self.assertTrue(usuario.consentimento_lgpd)
        self.assertIsNotNone(usuario.data_consentimento)

    def test_email_unico_sem_diferenciar_maiusculas(self):
        self.client.post(reverse("criar_usuario"), DADOS)
        outro = dict(DADOS, username="maria2", email="MARIA@unimontes.br")
        resposta = self.client.post(reverse("criar_usuario"), outro)
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(User.objects.count(), 1)

    def test_localizacao_fora_da_lista_e_recusada(self):
        self.client.post(reverse("criar_usuario"), dict(DADOS, localizacao="outra_cidade"))
        self.assertFalse(User.objects.exists())


class ConfirmacaoEmailTests(TestCase):
    """E1-02 · Confirmar e-mail para ativar a conta."""

    def setUp(self):
        self.usuario = User.objects.create_user(
            username="joao", email="joao@unimontes.br", password="SenhaForte#2026",
            whatsapp="38988880000", localizacao="centro", is_active=False,
        )

    def test_link_ativa_a_conta_uma_unica_vez(self):
        link = link_ativacao(self.usuario)
        self.assertEqual(self.client.get(link).status_code, 200)
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.is_active)
        self.assertEqual(self.client.get(link).status_code, 400)

    def test_link_adulterado_e_recusado(self):
        uid = urlsafe_base64_encode(force_bytes(self.usuario.pk))
        resposta = self.client.get(reverse("ativar_conta", args=[uid, "token-falso"]))
        self.assertEqual(resposta.status_code, 400)
        self.usuario.refresh_from_db()
        self.assertFalse(self.usuario.is_active)

    def test_login_bloqueado_enquanto_inativa(self):
        self.assertFalse(self.client.login(username="joao", password="SenhaForte#2026"))
        self.client.get(link_ativacao(self.usuario))
        self.assertTrue(self.client.login(username="joao", password="SenhaForte#2026"))

    def test_reenvio_do_link(self):
        resposta = self.client.post(reverse("confirme_email"), {"email": "joao@unimontes.br"})
        self.assertRedirects(resposta, reverse("confirme_email"))
        self.assertEqual(len(mail.outbox), 1)

    def test_reenvio_nao_revela_email_inexistente(self):
        resposta = self.client.post(
            reverse("confirme_email"), {"email": "ninguem@unimontes.br"}, follow=True
        )
        self.assertContains(resposta, "Se houver uma conta")
        self.assertEqual(len(mail.outbox), 0)
