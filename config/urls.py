from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="catalogo:busca", permanent=False), name="inicio"),
    path("admin/", admin.site.urls),
    path("usuarios/", include("usuarios.urls")),
    path("livros/", include("catalogo.urls")),
]
