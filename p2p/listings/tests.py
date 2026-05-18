from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from rest_framework.test import APIClient
from rest_framework import status

from .models import (
    Category, ItemType, Item,
    FavoriteItem, Notification,
    SharedRental, SharedRentalSegment,
)
from transactions.models import Transaction

User = get_user_model()


# ============================================================
# Helpers
# ============================================================

def make_user(email, username=None, phone=None, **kwargs):
    return User.objects.create_user(
        email=email,
        username=username or email.split('@')[0],
        password='TestPass123!',
        phone_number=phone or f'+7{email.replace("@", "").replace(".", "")[:10]}',
        **kwargs,
    )


def make_item(owner, name='Тестовый предмет', price='100.00', max_active_transactions=1):
    cat, _ = Category.objects.get_or_create(name='ТестКат')
    type_, _ = ItemType.objects.get_or_create(category=cat, name='ТестТип')
    return Item.objects.create(
        owner=owner,
        type=type_,
        name=name,
        description='описание',
        price=Decimal(price),
        max_active_transactions=max_active_transactions,
    )


def auth_client(user):
    from rest_framework_simplejwt.tokens import RefreshToken
    client = APIClient()
    token = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    return client


def future(days=1, hours=0):
    return timezone.now() + timedelta(days=days, hours=hours)


# ============================================================
# SharedRental — создание
# ============================================================

class SharedRentalCreateTests(TestCase):
    def setUp(self):
        self.owner = make_user('owner@x.com')
        self.creator = make_user('creator@x.com')
        self.item = make_item(self.owner)
        self.client_creator = auth_client(self.creator)
        self.client_owner = auth_client(self.owner)
        self.url = '/api/v1/listings/shared-rentals/'

    def _base_payload(self, **overrides):
        payload = {
            'item': self.item.id,
            'planned_start': future(days=1).isoformat(),
            'planned_end': future(days=5).isoformat(),
            'slots_needed': 2,
            'creator_segment_index': 0,
        }
        payload.update(overrides)
        return payload

    def test_create_happy_path(self):
        resp = self.client_creator.post(self.url, self._base_payload(), format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        self.assertEqual(resp.data['status'], 'collecting')
        self.assertEqual(len(resp.data['segments']), 2)
        # сегмент 0 у создателя, сегмент 1 свободен
        seg0 = next(s for s in resp.data['segments'] if s['segment_index'] == 0)
        seg1 = next(s for s in resp.data['segments'] if s['segment_index'] == 1)
        self.assertEqual(seg0['participant'], self.creator.id)
        self.assertIsNone(seg1['participant'])
        self.assertEqual(resp.data['days_per_slot'], 2)

    def test_planned_start_in_past_rejected(self):
        past = (timezone.now() - timedelta(days=1)).isoformat()
        resp = self.client_creator.post(self.url, self._base_payload(planned_start=past), format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_planned_end_before_start_rejected(self):
        end_before = future(days=2).isoformat()
        start_after = future(days=5).isoformat()
        resp = self.client_creator.post(
            self.url,
            self._base_payload(planned_start=start_after, planned_end=end_before),
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_period_not_divisible_rejected(self):
        # 5 дней / 2 слота = 2.5, не делится
        start = future(days=1)
        end = start + timedelta(days=5)  # Ровно 5 дней от start

        resp = self.client_creator.post(
            self.url,
            {
                'item': self.item.id,
                'planned_start': start.isoformat(),
                'planned_end': end.isoformat(),
                'slots_needed': 2,
                'creator_segment_index': 0,
            },
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_slots_needed_must_be_at_least_2(self):
        resp = self.client_creator.post(self.url, self._base_payload(slots_needed=1), format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_creator_cannot_rent_own_item(self):
        resp = self.client_owner.post(self.url, self._base_payload(), format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_segment_index_out_of_range(self):
        resp = self.client_creator.post(self.url, self._base_payload(creator_segment_index=5), format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_via_item_url(self):
        url = f'/api/v1/listings/{self.item.id}/shared-rentals/'
        payload = self._base_payload()
        payload.pop('item')  # item теперь из URL
        resp = self.client_creator.post(url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        self.assertEqual(resp.data['item'], self.item.id)


# ============================================================
# SharedRental — join / leave
# ============================================================

class SharedRentalJoinLeaveTests(TestCase):
    def setUp(self):
        self.owner = make_user('owner2@x.com')
        self.creator = make_user('creator2@x.com')
        self.partner = make_user('partner2@x.com')
        self.stranger = make_user('stranger2@x.com')
        self.item = make_item(self.owner)
        self.sr = SharedRental.objects.create(
            item=self.item, creator=self.creator,
            planned_start=future(days=1), planned_end=future(days=5),
            slots_needed=2,
        )
        # сегмент 0 — создатель, сегмент 1 — свободен
        SharedRentalSegment.objects.create(
            shared_rental=self.sr, segment_index=0,
            segment_start=self.sr.planned_start,
            segment_end=self.sr.planned_start + timedelta(days=2),
            participant=self.creator, joined_at=timezone.now(),
        )
        SharedRentalSegment.objects.create(
            shared_rental=self.sr, segment_index=1,
            segment_start=self.sr.planned_start + timedelta(days=2),
            segment_end=self.sr.planned_end,
        )

    def test_partner_joins_free_segment(self):
        c = auth_client(self.partner)
        resp = c.post(f'/api/v1/listings/shared-rentals/{self.sr.id}/join/', {'segment_index': 1}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertTrue(resp.data['is_full'])

    def test_partner_cannot_join_taken_segment(self):
        c = auth_client(self.partner)
        resp = c.post(f'/api/v1/listings/shared-rentals/{self.sr.id}/join/', {'segment_index': 0}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_owner_cannot_join_own_item(self):
        c = auth_client(self.owner)
        resp = c.post(f'/api/v1/listings/shared-rentals/{self.sr.id}/join/', {'segment_index': 1}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_creator_cannot_join_twice(self):
        c = auth_client(self.creator)
        resp = c.post(f'/api/v1/listings/shared-rentals/{self.sr.id}/join/', {'segment_index': 1}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_join_creates_notification_for_creator(self):
        c = auth_client(self.partner)
        c.post(f'/api/v1/listings/shared-rentals/{self.sr.id}/join/', {'segment_index': 1}, format='json')
        self.assertEqual(
            Notification.objects.filter(user=self.creator, kind='shared_rental_joined').count(),
            1,
        )

    def test_partner_leaves(self):
        # сначала присоединяется
        c = auth_client(self.partner)
        c.post(f'/api/v1/listings/shared-rentals/{self.sr.id}/join/', {'segment_index': 1}, format='json')
        # теперь выходит
        resp = c.post(f'/api/v1/listings/shared-rentals/{self.sr.id}/leave/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data['is_full'])

    def test_creator_cannot_leave(self):
        c = auth_client(self.creator)
        resp = c.post(f'/api/v1/listings/shared-rentals/{self.sr.id}/leave/')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# ============================================================
# SharedRental — approve / reject / FSM
# ============================================================

class SharedRentalApproveRejectTests(TestCase):
    def setUp(self):
        self.owner = make_user('owner3@x.com')
        self.creator = make_user('creator3@x.com')
        self.partner = make_user('partner3@x.com')
        self.item = make_item(self.owner)
        # создаём заявку и сразу заполняем оба слота
        c = auth_client(self.creator)
        resp = c.post('/api/v1/listings/shared-rentals/', {
            'item': self.item.id,
            'planned_start': future(days=1).isoformat(),
            'planned_end': future(days=5).isoformat(),
            'slots_needed': 2,
            'creator_segment_index': 0,
        }, format='json')
        self.sr_id = resp.data['id']
        auth_client(self.partner).post(
            f'/api/v1/listings/shared-rentals/{self.sr_id}/join/',
            {'segment_index': 1}, format='json',
        )

    def test_owner_approves_when_full(self):
        resp = auth_client(self.owner).post(f'/api/v1/listings/shared-rentals/{self.sr_id}/approve/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(resp.data['status'], 'approved')

    def test_non_owner_cannot_approve(self):
        resp = auth_client(self.creator).post(f'/api/v1/listings/shared-rentals/{self.sr_id}/approve/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_rejects(self):
        resp = auth_client(self.owner).post(f'/api/v1/listings/shared-rentals/{self.sr_id}/reject/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.sr_id_ = self.sr_id
        sr = SharedRental.objects.get(pk=self.sr_id)
        self.assertEqual(sr.status, 'cancelled')

    def test_approve_creates_notifications_for_participants(self):
        auth_client(self.owner).post(f'/api/v1/listings/shared-rentals/{self.sr_id}/approve/')
        for user in [self.creator, self.partner]:
            self.assertEqual(
                Notification.objects.filter(user=user, kind='shared_rental_approved').count(),
                1,
            )

    def test_approve_when_not_full_rejected(self):
        # создаём ещё одну заявку и НЕ заполняем
        c = auth_client(self.creator)
        resp = c.post('/api/v1/listings/shared-rentals/', {
            'item': self.item.id,
            'planned_start': future(days=10).isoformat(),
            'planned_end': future(days=14).isoformat(),
            'slots_needed': 2,
            'creator_segment_index': 0,
        }, format='json')
        sr2_id = resp.data['id']
        resp = auth_client(self.owner).post(f'/api/v1/listings/shared-rentals/{sr2_id}/approve/')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# ============================================================
# SharedRental — confirm-receipt / confirm-return / finalize
# ============================================================

class SharedRentalLifecycleTests(TestCase):
    def setUp(self):
        self.owner = make_user('owner4@x.com')
        self.creator = make_user('creator4@x.com')
        self.partner = make_user('partner4@x.com')
        self.stranger = make_user('stranger4@x.com')
        self.item = make_item(self.owner)
        c = auth_client(self.creator)
        resp = c.post('/api/v1/listings/shared-rentals/', {
            'item': self.item.id,
            'planned_start': future(days=1).isoformat(),
            'planned_end': future(days=5).isoformat(),
            'slots_needed': 2,
            'creator_segment_index': 0,
        }, format='json')
        self.sr_id = resp.data['id']
        auth_client(self.partner).post(
            f'/api/v1/listings/shared-rentals/{self.sr_id}/join/',
            {'segment_index': 1}, format='json',
        )
        auth_client(self.owner).post(f'/api/v1/listings/shared-rentals/{self.sr_id}/approve/')

    def test_full_lifecycle_to_completed(self):
        # creator confirms receipt
        r = auth_client(self.creator).post(f'/api/v1/listings/shared-rentals/{self.sr_id}/confirm-receipt/')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.data['status'], 'active')

        # partner confirms return
        r = auth_client(self.partner).post(f'/api/v1/listings/shared-rentals/{self.sr_id}/confirm-return/')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.data['status'], 'returning')

        # owner finalizes
        r = auth_client(self.owner).post(f'/api/v1/listings/shared-rentals/{self.sr_id}/finalize/')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.data['status'], 'completed')

    def test_stranger_cannot_confirm_receipt(self):
        r = auth_client(self.stranger).post(f'/api/v1/listings/shared-rentals/{self.sr_id}/confirm-receipt/')
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_cannot_confirm_receipt(self):
        r = auth_client(self.owner).post(f'/api/v1/listings/shared-rentals/{self.sr_id}/confirm-receipt/')
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_confirm_return_only_in_active(self):
        # сейчас approved, в active не переходили
        r = auth_client(self.creator).post(f'/api/v1/listings/shared-rentals/{self.sr_id}/confirm-return/')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_finalize_notifies_favoriters(self):
        # FAVORITER ставит лайк предмету
        FavoriteItem.objects.create(user=self.stranger, item=self.item)
        # прогоняем до completed
        auth_client(self.creator).post(f'/api/v1/listings/shared-rentals/{self.sr_id}/confirm-receipt/')
        auth_client(self.partner).post(f'/api/v1/listings/shared-rentals/{self.sr_id}/confirm-return/')
        auth_client(self.owner).post(f'/api/v1/listings/shared-rentals/{self.sr_id}/finalize/')
        self.assertEqual(
            Notification.objects.filter(user=self.stranger, kind='favorite_available').count(),
            1,
        )


# ============================================================
# SharedRental — destroy / запрет PUT/PATCH
# ============================================================

class SharedRentalDestroyTests(TestCase):
    def setUp(self):
        self.owner = make_user('owner5@x.com')
        self.creator = make_user('creator5@x.com')
        self.partner = make_user('partner5@x.com')
        self.item = make_item(self.owner)
        c = auth_client(self.creator)
        resp = c.post('/api/v1/listings/shared-rentals/', {
            'item': self.item.id,
            'planned_start': future(days=1).isoformat(),
            'planned_end': future(days=5).isoformat(),
            'slots_needed': 2,
            'creator_segment_index': 0,
        }, format='json')
        self.sr_id = resp.data['id']

    def test_only_creator_can_destroy(self):
        r = auth_client(self.partner).delete(f'/api/v1/listings/shared-rentals/{self.sr_id}/')
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_creator_destroys(self):
        r = auth_client(self.creator).delete(f'/api/v1/listings/shared-rentals/{self.sr_id}/')
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)
        sr = SharedRental.objects.get(pk=self.sr_id)
        self.assertEqual(sr.status, 'cancelled')

    def test_put_patch_forbidden(self):
        c = auth_client(self.creator)
        r = c.put(f'/api/v1/listings/shared-rentals/{self.sr_id}/', {})
        self.assertEqual(r.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        r = c.patch(f'/api/v1/listings/shared-rentals/{self.sr_id}/', {})
        self.assertEqual(r.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


# ============================================================
# Item.effective_status
# ============================================================

class ItemEffectiveStatusTests(TestCase):
    def setUp(self):
        self.owner = make_user('owner6@x.com')
        self.renter = make_user('renter6@x.com')
        self.item = make_item(self.owner)

    def test_effective_status_available_by_default(self):
        c = auth_client(self.owner)
        r = c.get(f'/api/v1/listings/item/{self.item.id}/')
        self.assertEqual(r.data['effective_status'], 'available')

    def test_effective_status_rented_when_transaction_active(self):
        Transaction.objects.create(
            item=self.item, renter=self.renter, owner=self.owner,
            status='active',
            planned_start=future(days=0), planned_end=future(days=2),
        )
        r = auth_client(self.owner).get(f'/api/v1/listings/item/{self.item.id}/')
        self.assertEqual(r.data['effective_status'], 'rented')

    def test_effective_status_rented_when_shared_rental_active(self):
        sr = SharedRental.objects.create(
            item=self.item, creator=self.renter,
            planned_start=future(days=1), planned_end=future(days=5),
            slots_needed=2, status='active',
        )
        r = auth_client(self.owner).get(f'/api/v1/listings/item/{self.item.id}/')
        self.assertEqual(r.data['effective_status'], 'rented')


# ============================================================
# /shared-rentals/pending/
# ============================================================

class SharedRentalPendingTests(TestCase):
    def setUp(self):
        self.owner = make_user('owner7@x.com')
        self.creator = make_user('creator7@x.com')
        self.partner = make_user('partner7@x.com')
        self.item = make_item(self.owner)
        c = auth_client(self.creator)
        resp = c.post('/api/v1/listings/shared-rentals/', {
            'item': self.item.id,
            'planned_start': future(days=1).isoformat(),
            'planned_end': future(days=5).isoformat(),
            'slots_needed': 2,
            'creator_segment_index': 0,
        }, format='json')
        self.sr_id = resp.data['id']
        auth_client(self.partner).post(
            f'/api/v1/listings/shared-rentals/{self.sr_id}/join/',
            {'segment_index': 1}, format='json',
        )

    def test_owner_sees_pending_when_full(self):
        # is_full=True, нужен approve от owner
        r = auth_client(self.owner).get('/api/v1/listings/shared-rentals/pending/')
        ids = [x['id'] for x in r.data.get('results', r.data)]
        self.assertIn(self.sr_id, ids)

    def test_participant_sees_pending_in_approved(self):
        auth_client(self.owner).post(f'/api/v1/listings/shared-rentals/{self.sr_id}/approve/')
        r = auth_client(self.creator).get('/api/v1/listings/shared-rentals/pending/')
        ids = [x['id'] for x in r.data.get('results', r.data)]
        self.assertIn(self.sr_id, ids)

    def test_stranger_sees_nothing(self):
        stranger = make_user('stranger7@x.com')
        r = auth_client(stranger).get('/api/v1/listings/shared-rentals/pending/')
        ids = [x['id'] for x in r.data.get('results', r.data)]
        self.assertEqual(ids, [])