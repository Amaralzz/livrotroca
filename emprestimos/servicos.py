"""Regras do fluxo de empréstimo e doação (RF06, RF07, RF08, RF09).

Cada transição trava a linha do livro no banco (select_for_update), para que
dois pedidos simultâneos não reservem o mesmo livro.
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from catalogo.models import Livro

from .models import Emprestimo

logger = logging.getLogger(__name__)


class RegraNegocio(Exception):
    """Ação não permitida pelas regras do LivroTroca."""


def _notificar(assunto, template, destinatario, pedido):
    contexto = {"pedido": pedido, "link": settings.SITE_URL + reverse("emprestimos:painel")}
    try:
        send_mail(
            subject=f"{assunto} · LivroTroca",
            message=render_to_string(template, contexto),
            from_email=None,
            recipient_list=[destinatario.email],
        )
    except Exception:  # falha no e-mail não desfaz o empréstimo
        logger.exception("Falha ao enviar e-mail '%s' para %s", assunto, destinatario.email)


def _travar(pedido_id):
    pedido = Emprestimo.objects.select_related("solicitante").get(pk=pedido_id)
    livro = Livro.objects.select_for_update().select_related("dono").get(pk=pedido.livro_id)
    pedido = Emprestimo.objects.select_for_update().select_related("solicitante").get(pk=pedido_id)
    pedido.livro = livro
    return pedido, livro


@transaction.atomic
def solicitar(livro_id, solicitante):
    """E4-01: o livro passa a "Reservado" e o dono é avisado."""
    livro = Livro.objects.select_for_update().select_related("dono").get(pk=livro_id)
    if livro.dono_id == solicitante.pk:
        raise RegraNegocio("Você não pode pedir o próprio livro.")
    if livro.status != Livro.Status.DISPONIVEL:
        raise RegraNegocio("Este livro não está disponível no momento.")

    pedido = Emprestimo.objects.create(
        livro=livro, solicitante=solicitante, modalidade=livro.modalidade
    )
    livro.status = Livro.Status.RESERVADO
    livro.save(update_fields=["status", "atualizado_em"])

    transaction.on_commit(lambda: _notificar(
        "Novo pedido", "emprestimos/email_novo_pedido.txt", livro.dono, pedido
    ))
    return pedido


@transaction.atomic
def aprovar(pedido_id, dono):
    """E4-02 + E5-01: aprova o pedido. No empréstimo, o prazo de 14 dias começa agora."""
    pedido, livro = _travar(pedido_id)
    if livro.dono_id != dono.pk:
        raise RegraNegocio("Só o dono do livro pode responder a este pedido.")
    if pedido.status != Emprestimo.Status.PENDENTE:
        raise RegraNegocio("Este pedido já foi respondido.")

    pedido.status = Emprestimo.Status.APROVADO
    pedido.respondido_em = timezone.now()
    if pedido.eh_doacao:
        # A doação fica reservada até o doador confirmar a entrega (E4-06)
        livro.status = Livro.Status.RESERVADO
    else:
        pedido.data_limite = timezone.localdate() + timedelta(days=Emprestimo.PRAZO_PADRAO_DIAS)
        livro.status = Livro.Status.EMPRESTADO
    pedido.save()
    livro.save(update_fields=["status", "atualizado_em"])

    transaction.on_commit(lambda: _notificar(
        "Pedido aprovado", "emprestimos/email_pedido_respondido.txt", pedido.solicitante, pedido
    ))
    return pedido


@transaction.atomic
def recusar(pedido_id, dono):
    """E4-02: recusa o pedido e o livro volta a "Disponível"."""
    pedido, livro = _travar(pedido_id)
    if livro.dono_id != dono.pk:
        raise RegraNegocio("Só o dono do livro pode responder a este pedido.")
    if pedido.status != Emprestimo.Status.PENDENTE:
        raise RegraNegocio("Este pedido já foi respondido.")

    pedido.status = Emprestimo.Status.RECUSADO
    pedido.respondido_em = timezone.now()
    pedido.save()
    livro.status = Livro.Status.DISPONIVEL
    livro.save(update_fields=["status", "atualizado_em"])

    transaction.on_commit(lambda: _notificar(
        "Pedido recusado", "emprestimos/email_pedido_respondido.txt", pedido.solicitante, pedido
    ))
    return pedido


@transaction.atomic
def confirmar_entrega_doacao(pedido_id, doador):
    """E4-06: o livro passa a "Doado" de forma permanente e sai da busca."""
    pedido, livro = _travar(pedido_id)
    if livro.dono_id != doador.pk:
        raise RegraNegocio("Só o doador pode confirmar a entrega.")
    if not pedido.eh_doacao or pedido.status != Emprestimo.Status.APROVADO:
        raise RegraNegocio("Só é possível confirmar a entrega de uma doação aprovada.")

    pedido.status = Emprestimo.Status.CONCLUIDO
    pedido.concluido_em = timezone.now()
    pedido.save()
    livro.status = Livro.Status.DOADO
    livro.save(update_fields=["status", "atualizado_em"])
    return pedido
