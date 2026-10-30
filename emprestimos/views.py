from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from catalogo.models import Livro

from . import servicos
from .models import Emprestimo


@login_required
def painel(request):
    """Pedidos recebidos (como dono) e pedidos feitos (como solicitante)."""
    base = Emprestimo.objects.select_related("livro", "livro__dono", "solicitante")
    contexto = {
        "recebidos": base.filter(livro__dono=request.user),
        "feitos": base.filter(solicitante=request.user),
    }
    return render(request, "emprestimos/painel.html", contexto)


@login_required
@require_POST
def solicitar(request, livro_pk):
    livro = get_object_or_404(Livro, pk=livro_pk)
    try:
        servicos.solicitar(livro.pk, request.user)
    except servicos.RegraNegocio as erro:
        messages.error(request, str(erro))
        return redirect("catalogo:detalhe", pk=livro.pk)
    messages.success(request, "Pedido enviado! O dono do livro foi avisado por e-mail.")
    return redirect("emprestimos:painel")


def _responder(request, pk, acao, sucesso):
    # Quem não é o dono recebe 404, sem saber que o pedido existe
    pedido = get_object_or_404(Emprestimo, pk=pk, livro__dono=request.user)
    try:
        acao(pedido.pk, request.user)
        messages.success(request, sucesso)
    except servicos.RegraNegocio as erro:
        messages.error(request, str(erro))
    return redirect("emprestimos:painel")


@login_required
@require_POST
def aprovar(request, pk):
    return _responder(request, pk, servicos.aprovar, "Pedido aprovado. O solicitante foi avisado.")


@login_required
@require_POST
def recusar(request, pk):
    return _responder(request, pk, servicos.recusar, "Pedido recusado. O livro voltou a ficar disponível.")


@login_required
@require_POST
def confirmar_entrega(request, pk):
    return _responder(
        request, pk, servicos.confirmar_entrega_doacao, "Entrega confirmada. Obrigado pela doação!"
    )
