from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


def buscar_por_usuario_ou_email(identificador):
    """Encontra a conta pelo nome de usuário ou pelo e-mail (sem diferenciar maiúsculas no e-mail)."""
    User = get_user_model()
    return (
        User.objects.filter(username=identificador).first()
        or User.objects.filter(email__iexact=identificador).first()
    )


class UsuarioOuEmailBackend(ModelBackend):
    """E1-03: permite entrar com o nome de usuário ou com o e-mail cadastrado.

    Contas inativas (e-mail não confirmado) não autenticam (E1-02).
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(get_user_model().USERNAME_FIELD)
        if not username or password is None:
            return None
        usuario = buscar_por_usuario_ou_email(username)
        if usuario is None:
            # Executa o hash mesmo assim, para o tempo de resposta não revelar se a conta existe
            get_user_model()().set_password(password)
            return None
        if usuario.check_password(password) and self.user_can_authenticate(usuario):
            return usuario
        return None
