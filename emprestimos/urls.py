from django.urls import path

from . import views

app_name = "emprestimos"

urlpatterns = [
    path("", views.painel, name="painel"),
    path("solicitar/<int:livro_pk>/", views.solicitar, name="solicitar"),
    path("<int:pk>/aprovar/", views.aprovar, name="aprovar"),
    path("<int:pk>/recusar/", views.recusar, name="recusar"),
    path("<int:pk>/confirmar-entrega/", views.confirmar_entrega, name="confirmar_entrega"),
]
