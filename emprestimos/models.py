from django.conf import settings
from django.db import models

from catalogo.models import Livro


class Emprestimo(models.Model):
    """Pedido de um livro, para empréstimo ou doação (RF06, RF07, RF09)."""

    PRAZO_PADRAO_DIAS = 14  # RF07

    class Status(models.TextChoices):
        PENDENTE = "pendente", "Aguardando aprovação"
        APROVADO = "aprovado", "Aprovado"
        RECUSADO = "recusado", "Recusado"
        CANCELADO = "cancelado", "Cancelado"
        EXPIRADO = "expirado", "Expirado"
        CONCLUIDO = "concluido", "Concluído"

    livro = models.ForeignKey(Livro, on_delete=models.PROTECT, related_name="pedidos")
    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pedidos_feitos"
    )
    modalidade = models.CharField(max_length=12, choices=Livro.Modalidade.choices)
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.PENDENTE, db_index=True
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    respondido_em = models.DateTimeField(null=True, blank=True)
    data_limite = models.DateField("prazo de devolução", null=True, blank=True)  # E5-01
    concluido_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "empréstimo ou doação"
        verbose_name_plural = "empréstimos e doações"

    def __str__(self):
        return f"{self.get_modalidade_display()} de {self.livro.titulo} para {self.solicitante}"

    @property
    def eh_doacao(self):
        return self.modalidade == Livro.Modalidade.DOACAO

    @property
    def contato_liberado(self):
        """Os contatos das duas partes aparecem depois da aprovação."""
        return self.status in (self.Status.APROVADO, self.Status.CONCLUIDO)
