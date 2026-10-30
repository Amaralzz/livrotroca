# LivroTroca

Plataforma P2P de empréstimo e doação de livros entre estudantes da Unimontes e vizinhos de Montes Claros.
Projeto da disciplina de Gerência de Processo de Software (Unimontes, 2026).

## Sprint 1 (06/10 a 06/11/2026)

| Item | Funcionalidade | Onde está |
| --- | --- | --- |
| E8-01 | Projeto Django + MySQL | `config/` |
| E8-02 | Celery + Celery Beat e SMTP | `config/celery.py`, `emprestimos/tasks.py`, `config/settings.py` |
| E8-05 | HTTPS/TLS em produção | `config/settings.py` (bloco "Segurança de transmissão") |
| E1-01 | Cadastro com contato, localização e consentimento LGPD | `usuarios/forms.py`, `usuarios/views.py` |
| E1-02 | Confirmação de e-mail | `usuarios/tokens.py`, `usuarios/views.py` |
| E1-03 | Login (usuário ou e-mail) e logout | `usuarios/backends.py`, `usuarios/forms.py` |
| E1-05 | Recuperação de senha (link de 30 min, uso único) | `usuarios/urls.py` |
| E2-01 | Cadastro de livro (máx. 20 ativos) | `catalogo/` |
| E2-03 | Editar, retirar e republicar livro | `catalogo/views.py` |
| E3-01 | Busca por título ou autor | `catalogo/views.py` |
| E4-01 | Solicitar empréstimo ou doação | `emprestimos/servicos.py` |
| E4-02 | Aprovar ou recusar, com e-mail | `emprestimos/servicos.py` |
| E5-01 | Prazo padrão de 14 dias | `emprestimos/servicos.py` |
| E4-06 | Confirmar entrega de doação | `emprestimos/servicos.py` |

## Como rodar (Windows)

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env        # depois preencha os valores do banco
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Acesse http://127.0.0.1:8000. Sem SMTP configurado, os e-mails aparecem no terminal.

## Testes

```
python manage.py test
```

O usuário do MySQL precisa de permissão para criar o banco de testes.

## Celery (tarefas agendadas)

O Celery precisa de um Redis rodando (no Windows: Memurai, WSL ou Docker com `docker run -p 6379:6379 redis`).
Em dois terminais:

```
celery -A config worker --pool=solo -l info
celery -A config beat -l info
```

A tarefa de teste `verificar_agendador` roda a cada 15 minutos. As tarefas de expiração de reservas (E4-03) e de atraso (E5-02) entram na Sprint 2.

## E-mail real (SMTP)

No `.env`, troque `EMAIL_BACKEND` por `django.core.mail.backends.smtp.EmailBackend` e preencha `EMAIL_HOST_USER` e `EMAIL_HOST_PASSWORD`.
No Gmail, use uma "senha de app", não a senha da conta.

## Produção com HTTPS (E8-05)

Com `DEBUG=False`, o projeto redireciona para HTTPS, usa cookies seguros e ativa HSTS.
Para publicar (por exemplo no PythonAnywhere, que já oferece HTTPS):

1. Configure `DEBUG=False`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` e `SITE_URL` no `.env` do servidor.
2. Rode `python manage.py collectstatic` e `python manage.py check --deploy`.
