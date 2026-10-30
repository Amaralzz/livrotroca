from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from catalogo.models import Livro

from .models import Emprestimo

User = get_user_model()


def criar_usuario(username):
    return User.objects.create_user(
        username=username, email=f"{username}@unimontes.br", password="SenhaForte#2026",
        whatsapp="3899999" + str(len(username)).zfill(4), localizacao="campus_1",
    )


class FluxoBase(TestCase):
    modalidade = "emprestimo"

    def setUp(self):
        self.dono = criar_usuario("joao")
        self.leitor = criar_usuario("maria")
        self.livro = Livro.objects.create(
            dono=self.dono, titulo="Dom Casmurro", autor="Machado de Assis",
            conservacao="bom", modalidade=self.modalidade,
        )

    def solicitar(self, usuario=None):
        self.client.force_login(usuario or self.leitor)
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(reverse("emprestimos:solicitar", args=[self.livro.pk]))

    def responder(self, acao, usuario=None):
        pedido = Emprestimo.objects.get()
        self.client.force_login(usuario or self.dono)
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(reverse(f"emprestimos:{acao}", args=[pedido.pk]))

    def status_livro(self):
        self.livro.refresh_from_db()
        return self.livro.status


class SolicitarTests(FluxoBase):
    """E4-01 · Solicitar empréstimo."""

    def test_livro_fica_reservado_e_dono_e_notificado(self):
        resposta = self.solicitar()
        self.assertRedirects(resposta, reverse("emprestimos:painel"))
        self.assertEqual(self.status_livro(), Livro.Status.RESERVADO)
        self.assertEqual(Emprestimo.objects.get().status, Emprestimo.Status.PENDENTE)
        self.assertEqual(mail.outbox[0].to, ["joao@unimontes.br"])
        self.assertIn("Dom Casmurro", mail.outbox[0].body)

    def test_nao_pode_pedir_o_proprio_livro(self):
        self.solicitar(self.dono)
        self.assertFalse(Emprestimo.objects.exists())
        self.assertEqual(self.status_livro(), Livro.Status.DISPONIVEL)

    def test_nao_pode_pedir_livro_reservado(self):
        self.solicitar()
        self.solicitar(criar_usuario("carlos"))
        self.assertEqual(Emprestimo.objects.count(), 1)

    def test_visitante_precisa_entrar(self):
        resposta = self.client.post(reverse("emprestimos:solicitar", args=[self.livro.pk]))
        self.assertEqual(resposta.status_code, 302)
        self.assertIn(reverse("entrar"), resposta.url)


class AprovarRecusarTests(FluxoBase):
    """E4-02 · Aprovar ou recusar solicitação, e E5-01 · Prazo padrão de 14 dias."""

    def test_aprovacao_empresta_e_define_prazo_de_14_dias(self):
        self.solicitar()
        mail.outbox.clear()
        self.responder("aprovar")
        pedido = Emprestimo.objects.get()
        self.assertEqual(self.status_livro(), Livro.Status.EMPRESTADO)
        self.assertEqual(pedido.status, Emprestimo.Status.APROVADO)
        self.assertEqual(pedido.data_limite, timezone.localdate() + timedelta(days=14))
        self.assertEqual(mail.outbox[0].to, ["maria@unimontes.br"])
        self.assertIn("aprovado", mail.outbox[0].body)

    def test_prazo_e_contato_visiveis_para_as_duas_partes(self):
        self.solicitar()
        self.responder("aprovar")
        prazo = (timezone.localdate() + timedelta(days=14)).strftime("%d/%m/%Y")
        for usuario, contato in ((self.dono, self.leitor.whatsapp), (self.leitor, self.dono.whatsapp)):
            self.client.force_login(usuario)
            resposta = self.client.get(reverse("emprestimos:painel"))
            self.assertContains(resposta, f"Devolução até {prazo}")
            self.assertContains(resposta, contato)

    def test_contato_oculto_antes_da_aprovacao(self):
        self.solicitar()
        resposta = self.client.get(reverse("emprestimos:painel"))
        self.assertNotContains(resposta, self.dono.whatsapp)

    def test_recusa_devolve_o_livro_ao_catalogo(self):
        self.solicitar()
        mail.outbox.clear()
        self.responder("recusar")
        self.assertEqual(self.status_livro(), Livro.Status.DISPONIVEL)
        self.assertEqual(Emprestimo.objects.get().status, Emprestimo.Status.RECUSADO)
        self.assertIn("recusado", mail.outbox[0].body)

    def test_so_o_dono_responde(self):
        self.solicitar()
        resposta = self.responder("aprovar", usuario=self.leitor)
        self.assertEqual(resposta.status_code, 404)
        self.assertEqual(self.status_livro(), Livro.Status.RESERVADO)

    def test_pedido_ja_respondido_nao_muda(self):
        self.solicitar()
        self.responder("recusar")
        self.responder("aprovar")
        self.assertEqual(Emprestimo.objects.get().status, Emprestimo.Status.RECUSADO)
        self.assertEqual(self.status_livro(), Livro.Status.DISPONIVEL)


class DoacaoTests(FluxoBase):
    """E4-06 · Confirmar entrega de doação."""

    modalidade = "doacao"

    def test_fluxo_completo_da_doacao(self):
        self.solicitar()
        self.responder("aprovar")
        pedido = Emprestimo.objects.get()
        self.assertIsNone(pedido.data_limite)
        self.assertEqual(self.status_livro(), Livro.Status.RESERVADO)

        self.responder("confirmar_entrega")
        self.assertEqual(self.status_livro(), Livro.Status.DOADO)
        self.assertEqual(Emprestimo.objects.get().status, Emprestimo.Status.CONCLUIDO)

    def test_doado_sai_da_busca_e_fica_no_perfil_do_doador(self):
        self.solicitar()
        self.responder("aprovar")
        self.responder("confirmar_entrega")
        busca = self.client.get(reverse("catalogo:busca"), {"q": "Casmurro"})
        self.assertEqual(len(busca.context["pagina"]), 0)
        perfil = self.client.get(reverse("perfil", args=["joao"]))
        self.assertIn(self.livro, perfil.context["doacoes"])

    def test_nao_confirma_entrega_antes_da_aprovacao(self):
        self.solicitar()
        self.responder("confirmar_entrega")
        self.assertEqual(self.status_livro(), Livro.Status.RESERVADO)

    def test_nao_confirma_entrega_de_emprestimo(self):
        Livro.objects.filter(pk=self.livro.pk).update(modalidade="emprestimo")
        self.solicitar()
        self.responder("aprovar")
        self.responder("confirmar_entrega")
        self.assertEqual(self.status_livro(), Livro.Status.EMPRESTADO)
