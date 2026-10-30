import time

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import LIMITE_LIVROS_ATIVOS, Livro

User = get_user_model()


def criar_usuario(username):
    return User.objects.create_user(
        username=username, email=f"{username}@unimontes.br", password="SenhaForte#2026",
        whatsapp="38999990000", localizacao="campus_1",
    )


def criar_livro(dono, titulo="Dom Casmurro", autor="Machado de Assis", **extra):
    dados = {"conservacao": "bom", "modalidade": "emprestimo"}
    dados.update(extra)
    return Livro.objects.create(dono=dono, titulo=titulo, autor=autor, **dados)


DADOS_LIVRO = {
    "titulo": "Vidas Secas", "autor": "Graciliano Ramos",
    "conservacao": "bom", "modalidade": "doacao",
}


class CadastroLivroTests(TestCase):
    """E2-01 · Cadastrar livro."""

    def setUp(self):
        self.dono = criar_usuario("joao")
        self.client.force_login(self.dono)

    def test_cadastra_livro_disponivel(self):
        resposta = self.client.post(reverse("catalogo:novo"), DADOS_LIVRO)
        self.assertRedirects(resposta, reverse("catalogo:meus"))
        livro = Livro.objects.get()
        self.assertEqual(livro.dono, self.dono)
        self.assertEqual(livro.status, Livro.Status.DISPONIVEL)
        self.assertEqual(livro.modalidade, "doacao")

    def test_conservacao_e_modalidade_validas(self):
        self.client.post(reverse("catalogo:novo"), dict(DADOS_LIVRO, conservacao="otimo"))
        self.client.post(reverse("catalogo:novo"), dict(DADOS_LIVRO, modalidade="venda"))
        self.assertFalse(Livro.objects.exists())

    def test_limite_de_20_livros_ativos(self):
        for i in range(LIMITE_LIVROS_ATIVOS):
            criar_livro(self.dono, titulo=f"Livro {i}")
        resposta = self.client.post(reverse("catalogo:novo"), DADOS_LIVRO, follow=True)
        self.assertContains(resposta, "o máximo permitido")
        self.assertEqual(Livro.objects.count(), LIMITE_LIVROS_ATIVOS)

    def test_doados_e_retirados_nao_contam_no_limite(self):
        for i in range(LIMITE_LIVROS_ATIVOS - 1):
            criar_livro(self.dono, titulo=f"Livro {i}")
        criar_livro(self.dono, titulo="Doado", status=Livro.Status.DOADO)
        criar_livro(self.dono, titulo="Retirado", status=Livro.Status.RETIRADO)
        self.client.post(reverse("catalogo:novo"), DADOS_LIVRO)
        self.assertTrue(Livro.objects.filter(titulo="Vidas Secas").exists())

    def test_exige_login(self):
        self.client.logout()
        resposta = self.client.get(reverse("catalogo:novo"))
        self.assertEqual(resposta.status_code, 302)


class BuscaTests(TestCase):
    """E3-01 · Buscar livros por título ou autor."""

    def setUp(self):
        dono = criar_usuario("joao")
        criar_livro(dono, "Dom Casmurro", "Machado de Assis")
        criar_livro(dono, "1984", "George Orwell")
        criar_livro(dono, "A Revolução dos Bichos", "George Orwell")
        criar_livro(dono, "Vidas Secas", "Graciliano Ramos", status=Livro.Status.DOADO)
        criar_livro(dono, "Grande Sertão", "Guimarães Rosa", status=Livro.Status.RETIRADO)

    def titulos(self, q):
        resposta = self.client.get(reverse("catalogo:busca"), {"q": q})
        self.assertEqual(resposta.status_code, 200)
        return {livro.titulo for livro in resposta.context["pagina"]}

    def test_visitante_pode_buscar_por_titulo_parcial(self):
        self.assertEqual(self.titulos("casm"), {"Dom Casmurro"})

    def test_busca_por_autor_sem_diferenciar_maiusculas(self):
        self.assertEqual(self.titulos("ORWELL"), {"1984", "A Revolução dos Bichos"})

    def test_doados_e_retirados_nao_aparecem(self):
        self.assertEqual(self.titulos(""), {"Dom Casmurro", "1984", "A Revolução dos Bichos"})

    def test_busca_responde_em_menos_de_2_segundos(self):
        dono = User.objects.get(username="joao")
        Livro.objects.bulk_create([
            Livro(dono=dono, titulo=f"Livro {i}", autor=f"Autor {i}", conservacao="bom", modalidade="emprestimo")
            for i in range(1000)
        ])
        inicio = time.perf_counter()
        self.client.get(reverse("catalogo:busca"), {"q": "autor 99"})
        self.assertLess(time.perf_counter() - inicio, 2)


class DetalheLivroTests(TestCase):
    def setUp(self):
        self.dono = criar_usuario("joao")
        self.livro = criar_livro(self.dono)

    def test_visitante_ve_a_ficha_do_livro(self):
        resposta = self.client.get(reverse("catalogo:detalhe", args=[self.livro.pk]))
        self.assertContains(resposta, "Dom Casmurro")
        self.assertContains(resposta, "Campus I - Unimontes Montes Claros")
        self.assertContains(resposta, "Cadastre-se")

    def test_dono_ve_atalho_para_meus_livros(self):
        self.client.force_login(self.dono)
        resposta = self.client.get(reverse("catalogo:detalhe", args=[self.livro.pk]))
        self.assertContains(resposta, "Ver em Meus livros")

    def test_livro_doado_nao_abre_para_outros(self):
        Livro.objects.filter(pk=self.livro.pk).update(status=Livro.Status.DOADO)
        resposta = self.client.get(reverse("catalogo:detalhe", args=[self.livro.pk]))
        self.assertEqual(resposta.status_code, 404)
