from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import LivroForm
from .models import LIMITE_LIVROS_ATIVOS, Livro

MSG_LIMITE = (
    f"Você já tem {LIMITE_LIVROS_ATIVOS} livros ativos, o máximo permitido. "
    "Retire um anúncio para cadastrar outro."
)


def busca(request):
    """E3-01: busca por título ou autor, aberta também a visitantes."""
    q = request.GET.get("q", "").strip()
    livros = Livro.objects.visiveis().select_related("dono")
    if q:
        livros = livros.filter(Q(titulo__icontains=q) | Q(autor__icontains=q))
    pagina = Paginator(livros, 20).get_page(request.GET.get("page"))
    return render(request, "catalogo/busca.html", {"pagina": pagina, "q": q})


def detalhe(request, pk):
    livro = get_object_or_404(Livro.objects.select_related("dono"), pk=pk)
    eh_dono = request.user.is_authenticated and livro.dono_id == request.user.pk
    if livro.status not in Livro.STATUS_ATIVOS and not eh_dono:
        raise Http404("Livro indisponível.")
    contexto = {
        "livro": livro,
        "eh_dono": eh_dono,
        "pode_solicitar": (
            request.user.is_authenticated
            and not eh_dono
            and livro.status == Livro.Status.DISPONIVEL
        ),
    }
    return render(request, "catalogo/detalhe.html", contexto)


@login_required
def meus_livros(request):
    livros = Livro.objects.filter(dono=request.user)
    contexto = {
        "livros": livros,
        "ativos": livros.ativos().count(),
        "limite": LIMITE_LIVROS_ATIVOS,
    }
    return render(request, "catalogo/meus.html", contexto)


@login_required
def novo_livro(request):
    """E2-01: cadastrar livro, respeitando o máximo de 20 livros ativos."""
    if Livro.limite_atingido(request.user):
        messages.error(request, MSG_LIMITE)
        return redirect("catalogo:meus")

    form = LivroForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        livro = form.save(commit=False)
        livro.dono = request.user
        livro.save()
        messages.success(request, f"\"{livro.titulo}\" foi publicado.")
        return redirect("catalogo:meus")
    contexto = {"form": form, "titulo_pagina": "Cadastrar livro", "botao": "Publicar livro"}
    return render(request, "catalogo/form.html", contexto)


@login_required
def editar_livro(request, pk):
    """E2-03: editar dados do livro, bloqueado durante reserva ou empréstimo."""
    livro = get_object_or_404(Livro, pk=pk, dono=request.user)
    if not livro.pode_editar:
        messages.error(request, "Não é possível editar um livro reservado, emprestado ou doado.")
        return redirect("catalogo:meus")

    form = LivroForm(request.POST or None, instance=livro)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Alterações salvas.")
        return redirect("catalogo:meus")
    contexto = {"form": form, "titulo_pagina": "Editar livro", "botao": "Salvar alterações"}
    return render(request, "catalogo/form.html", contexto)


@login_required
@require_POST
def retirar_livro(request, pk):
    """E2-03: retirar o anúncio (só de livros disponíveis)."""
    livro = get_object_or_404(Livro, pk=pk, dono=request.user)
    if not livro.pode_retirar:
        messages.error(request, "Só é possível retirar o anúncio de um livro disponível.")
    else:
        livro.status = Livro.Status.RETIRADO
        livro.save(update_fields=["status", "atualizado_em"])
        messages.success(request, f"O anúncio de \"{livro.titulo}\" foi retirado.")
    return redirect("catalogo:meus")


@login_required
@require_POST
def republicar_livro(request, pk):
    """E2-03: voltar a anunciar um livro retirado."""
    livro = get_object_or_404(Livro, pk=pk, dono=request.user, status=Livro.Status.RETIRADO)
    if Livro.limite_atingido(request.user):
        messages.error(request, MSG_LIMITE)
    else:
        livro.status = Livro.Status.DISPONIVEL
        livro.save(update_fields=["status", "atualizado_em"])
        messages.success(request, f"\"{livro.titulo}\" está disponível de novo.")
    return redirect("catalogo:meus")
