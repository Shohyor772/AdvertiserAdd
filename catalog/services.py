"""Business transitions shared by HTTP, admin and scheduled jobs."""
from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from .models import Deal, LedgerEntry, Notification, Dispute, Payment, ChatMessage


def notify(user_id, text, link=''):
    # The in-app audit inbox is retained even when browser notifications are off.
    Notification.objects.create(user_id=user_id, text=text, link=link)


def participant(proposal, user, staff=False):
    if user.pk not in [proposal.advertiser_id, proposal.blogger.user_id] and not (staff and user.is_staff):
        raise PermissionDenied('Нет доступа к этой переписке.')


def require_role(user, role):
    if user.user_type != role:
        raise PermissionDenied('Это действие доступно только для роли: '+role)


def agreement(proposal, user):
    participant(proposal, user)
    if proposal.status != 'sent':
        raise ValidationError('Предложение уже закрыто.')
    last = proposal.last_offer_by_id or proposal.advertiser_id
    if user.pk == last:
        raise ValidationError('Подтвердить цену должен другой участник.')
    amount = proposal.counter_price if proposal.counter_price is not None else proposal.price
    proposal.price = amount
    proposal.status = 'agreed'
    proposal.save(update_fields=['price', 'status'])
    deal = Deal.objects.create(proposal=proposal, amount=amount, commission=amount * settings.COMMISSION_PERCENT // 100)
    for uid in [proposal.advertiser_id, proposal.blogger.user_id]:
        notify(uid, 'Условия согласованы. Ожидается оплата.', f'#/chats/{proposal.pk}')
    return deal


@transaction.atomic
def confirm_test_payment(deal_id, user):
    if settings.PAYMENT_MODE != 'test' or not settings.DEBUG:
        raise ValidationError('Учебные сделки отключены в настройках приложения.')
    deal = Deal.objects.select_for_update(of=('self',)).select_related('proposal__blogger').get(pk=deal_id)
    if user.pk != deal.proposal.advertiser_id:
        raise PermissionDenied()
    if deal.status != 'awaiting_payment':
        raise ValidationError('Сделка уже оплачена или закрыта.')
    payment, _ = Payment.objects.get_or_create(deal=deal, defaults={'is_test': True})
    payment.status = 'held'
    payment.save(update_fields=['status'])
    LedgerEntry.objects.create(deal=deal, kind='hold', amount=deal.amount)
    deal.status = 'in_progress'
    deal.save(update_fields=['status', 'updated_at'])
    notify(deal.proposal.blogger.user_id, 'Тестовый резерв создан. Можно приступать к работе.', f'#/chats/{deal.proposal_id}')
    return deal


def settle_locked(deal, refund=False):
    if not hasattr(deal, 'payment') or deal.payment.status != 'held':
        raise ValidationError('Для сделки нет зарезервированных средств.')
    # A production payout adapter must perform real transfer before marking paid.
    if not deal.payment.is_test:
        raise ValidationError('Эта версия поддерживает только учебные сделки.')
    kind = 'refund' if refund else 'payout'
    LedgerEntry.objects.create(deal=deal, kind=kind, amount=deal.amount if refund else deal.amount-deal.commission)
    if not refund:
        LedgerEntry.objects.create(deal=deal, kind='commission', amount=deal.commission)
    deal.payment.status = 'refunded' if refund else 'paid'
    deal.payment.save(update_fields=['status'])
    deal.status = 'refunded' if refund else 'completed'
    deal.completed_at = timezone.now()
    deal.save(update_fields=['status', 'completed_at', 'updated_at'])
    for uid in [deal.proposal.advertiser_id, deal.proposal.blogger.user_id]:
        notify(uid, 'Тестовая сделка: возврат выполнен.' if refund else 'Тестовая сделка завершена. Оцените партнёра.', f'#/chats/{deal.proposal_id}')


@transaction.atomic
def complete(deal_id, user=None, automatic=False):
    deal = Deal.objects.select_for_update(of=('self',)).select_related('proposal__blogger', 'payment').get(pk=deal_id)
    if user and user.pk != deal.proposal.advertiser_id:
        raise PermissionDenied()
    if deal.status != 'submitted':
        raise ValidationError('Принимать можно только сданную работу.')
    if automatic and (not deal.submitted_at or deal.submitted_at > timezone.now()-timedelta(days=3)):
        raise ValidationError('Срок автоматической приёмки ещё не наступил.')
    settle_locked(deal)
    return deal


@transaction.atomic
def resolve_dispute(dispute_id, admin, decision, reason):
    if not admin.is_staff:
        raise PermissionDenied()
    # Always lock the deal first; other actions use the same lock order.
    did = Dispute.objects.get(pk=dispute_id).deal_id
    deal = Deal.objects.select_for_update(of=('self',)).select_related('proposal__blogger', 'payment').get(pk=did)
    dispute = Dispute.objects.select_for_update(of=('self',)).get(pk=dispute_id)
    if deal.status != 'disputed' or dispute.resolved_at:
        raise ValidationError('Спор уже закрыт.')
    if decision not in ['blogger', 'advertiser'] or not reason.strip():
        raise ValidationError('Укажите решение и обоснование.')
    settle_locked(deal, refund=decision == 'advertiser')
    dispute.decision = decision
    dispute.resolution = reason
    dispute.resolved_by = admin
    dispute.resolved_at = timezone.now()
    dispute.save()
    ChatMessage.objects.create(proposal=deal.proposal, sender=admin, text='Решение арбитража: '+reason)
    return dispute
