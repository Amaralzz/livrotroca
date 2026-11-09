from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.crypto import constant_time_compare
from django.utils.http import base36_to_int


class TokenAtivacaoConta(PasswordResetTokenGenerator):
    """Token do link de confirmação de e-mail (E1-02).

    Inclui is_active no hash: depois que a conta é ativada, o link deixa de valer.
    Tem validade própria (settings.ATIVACAO_TIMEOUT), separada do link de
    redefinição de senha (settings.PASSWORD_RESET_TIMEOUT, 30 min).
    """

    key_salt = "livrotroca.usuarios.tokens.TokenAtivacaoConta"

    def _make_hash_value(self, usuario, timestamp):
        return f"{usuario.pk}{timestamp}{usuario.is_active}"

    def check_token(self, usuario, token):
        if not (usuario and token):
            return False
        try:
            ts_b36, _ = token.split("-")
            ts = base36_to_int(ts_b36)
        except ValueError:
            return False
        for secret in [self.secret, *self.secret_fallbacks]:
            if constant_time_compare(self._make_token_with_timestamp(usuario, ts, secret), token):
                break
        else:
            return False
        return (self._num_seconds(self._now()) - ts) <= settings.ATIVACAO_TIMEOUT


gerador_token_ativacao = TokenAtivacaoConta()
