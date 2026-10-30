from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    class Localizacao(models.TextChoices):
        CAMPUS_I = "campus_1", "Campus I - Unimontes Montes Claros"
        CAMPUS_II = "campus_2", "Campus II - Unimontes Januária"
        CENTRO = "centro", "Centro"
        IBITURUNA = "ibituruna", "Bairro Ibituruna"
        TODOS_OS_SANTOS = "todos_os_santos", "Bairro Todos os Santos"

    email = models.EmailField(unique=True)
    whatsapp = models.CharField(max_length=20)
    localizacao = models.CharField(max_length=20, choices=Localizacao.choices)

    # LGPD (RNF04): registro do consentimento explícito dado no cadastro
    consentimento_lgpd = models.BooleanField(default=False)
    data_consentimento = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.username
