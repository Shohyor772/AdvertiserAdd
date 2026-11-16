from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from django.db import connection, connections
from django.test import TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from users.models import User
from .models import BloggerProfile, Proposal, Deal, LedgerEntry
from .services import confirm_test_payment, complete


@skipUnless(connection.vendor == 'postgresql', 'Row-lock concurrency requires PostgreSQL')
@override_settings(PAYMENT_MODE='test', DEBUG=True)
class ConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.ad=User.objects.create_user('concurrent-ad',user_type='advertiser',email_verified=True)
        b=User.objects.create_user('concurrent-blogger')
        profile=BloggerProfile.objects.create(user=b)
        p=Proposal.objects.create(advertiser=self.ad,blogger=profile,price=1000,status='agreed')
        self.deal=Deal.objects.create(proposal=p,amount=1000,commission=100)

    def twice(self, operation):
        barrier=Barrier(2)
        def run():
            connections.close_all()
            try:
                barrier.wait(timeout=10)
                operation()
                return 'ok'
            except ValidationError:
                return 'rejected'
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:run(),range(2)))
        self.assertCountEqual(results,['ok','rejected'])

    def test_parallel_payment_creates_one_reserve(self):
        self.twice(lambda:confirm_test_payment(self.deal.pk,self.ad))
        self.assertEqual(LedgerEntry.objects.filter(deal=self.deal,kind='hold').count(),1)

    def test_parallel_acceptance_creates_one_payout(self):
        confirm_test_payment(self.deal.pk,self.ad)
        Deal.objects.filter(pk=self.deal.pk).update(status='submitted',submitted_at=timezone.now(),publication_url='https://t.me/test/1')
        self.twice(lambda:complete(self.deal.pk,self.ad))
        self.assertEqual(LedgerEntry.objects.filter(deal=self.deal,kind='payout').count(),1)
