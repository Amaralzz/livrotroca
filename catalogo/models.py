from django.conf import settings
from django.db import models

LIMITE_LIVROS_ATIVOS = 20  # RF04


class LivroQuerySet(models.QuerySet):
    def ativos(self):
        """Livros que contam no limite de 20 por membro (não doados nem retirados)."""
        return self.filter(status__in=Livro.STATUS_ATIVOS)

    def visiveis(self):
        """Livros que aparecem na busca. Doados e retirados nunca aparecem (RF09)."""
        return self.filter(status__in=Livro.STATUS_ATIVOS)


class Livro(models.Model):
    """Livro do acervo pessoal de um membro (RF04)."""

    class Conservacao(models.TextChoices):
        NOVO = "novo", "Novo"
        BOM = "bom", "Bom"
        REGULAR = "regular", "Regular"
        DANIFICADO = "danificado", "Danificado"

    class Modalidade(models.TextChoices):
        EMPRESTIMO = "emprestimo", "Empréstimo"
        DOACAO = "doacao", "Doação"

    class Status(models.TextChoices):
        # Sequência do RF06: Disponível -> Reservado -> Emprestado -> Em atraso -> (devolvido) Disponível
        DISPONIVEL = "disponivel", "Disponível"
        RESERVADO = "reservado", "Reservado"
        EMPRESTADO = "emprestado", "Emprestado"
        EM_ATRASO = "em_atraso", "Em atraso"
        DOADO = "doado", "Doado"
        RETIRADO = "retirado", "Anúncio retirado"

    STATUS_ATIVOS = (Status.DISPONIVEL, Status.RESERVADO, Status.EMPRESTADO, Status.EM_ATRASO)
    STATUS_EDITAVEIS = (Status.DISPONIVEL, Status.RETIRADO)

    dono = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="livros"
    )
    titulo = models.CharField("título", max_length=200, db_index=True)
    autor = models.CharField(max_length=200, db_index=True)
    conservacao = models.CharField(
        "estado de conservação", max_length=12, choices=Conservacao.choices
    )
    modalidade = models.CharField(max_length=12, choices=Modalidade.choices)
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.DISPONIVEL, db_index=True
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    objects = LivroQuerySet.as_manager()

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.titulo} ({self.autor})"

    @property
    def pode_editar(self):
        """E2-03: edição bloqueada durante empréstimo ou reserva."""
        return self.status in self.STATUS_EDITAVEIS

    @property
    def pode_retirar(self):
        """E2-03: só livros disponíveis podem ter o anúncio retirado."""
        return self.status == self.Status.DISPONIVEL

    @property
    def eh_doacao(self):
        return self.modalidade == self.Modalidade.DOACAO

    @classmethod
    def limite_atingido(cls, usuario):
        return cls.objects.filter(dono=usuario).ativos().count() >= LIMITE_LIVROS_ATIVOS
