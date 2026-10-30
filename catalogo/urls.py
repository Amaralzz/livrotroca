from django.urls import path

from . import views

app_name = "catalogo"

urlpatterns = [
    path("", views.busca, name="busca"),
    path("meus/", views.meus_livros, name="meus"),
    path("novo/", views.novo_livro, name="novo"),
    path("<int:pk>/", views.detalhe, name="detalhe"),
]
