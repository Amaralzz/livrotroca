import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def verificar_agendador():
    """Tarefa de teste do Celery Beat (E8-02).

    Confirma que o worker e o agendador estão rodando. As tarefas reais
    (expirar reservas em 48h e marcar atrasos) entram na Sprint 2 (E4-03, E5-02).
    """
    agora = timezone.now().isoformat()
    logger.info("Celery Beat ativo em %s", agora)
    return agora
