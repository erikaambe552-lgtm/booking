"""Functional, security and concurrency tests.

    python manage.py test            (needs PostgreSQL; creates a test database)

The concurrency tests use real OS threads, each with its OWN PostgreSQL
connection, released at the same instant by a threading.Barrier — so the
requests genuinely overlap inside the database.
"""
import threading
import time
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import IntegrityError, connection, transaction
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Role
from destinations.models import BeachVenue, Destination, MountainGuide

from . import services
from .models import BeachReservation, BookingStatus, GuideReservation, GuideSchedule, VenueSlot


def make_world():
    beach = Destination.objects.create(name="Test Beach", category="BEACH", municipality="Almeria",
                                       short_description="t", is_verified=True, booking_enabled=True)
    mountain = Destination.objects.create(name="Test Mountain", category="MOUNTAIN", municipality="Almeria",
                                          short_description="t", is_verified=True, booking_enabled=True)
    closed = Destination.objects.create(name="Unverified Beach", category="BEACH", short_description="t")
    op = User.objects.create_user("op", password="Op-pass-123!")
    op.profile.role = Role.VENUE_OPERATOR
    op.profile.save()
    gu = User.objects.create_user("gu", password="Gu-pass-123!")
    gu.profile.role = Role.GUIDE
    gu.profile.save()
    venue = BeachVenue.objects.create(destination=beach, name="V1", operator=op, base_price=Decimal("500"),
                                      included_guests=4, price_per_extra_guest=Decimal("50"), max_guests=10,
                                      is_verified=True)
    guide = MountainGuide.objects.create(destination=mountain, display_name="G1", user=gu,
                                         price_per_group=Decimal("1500"), price_per_participant=Decimal("100"),
                                         max_participants=8, is_verified=True)
    start = timezone.now() + timedelta(days=3)
    slot = VenueSlot.objects.create(venue=venue, start_at=start, end_at=start + timedelta(hours=12))
    sched = GuideSchedule.objects.create(guide=guide, start_at=start, end_at=start + timedelta(hours=10))
    return dict(beach=beach, mountain=mountain, closed=closed, venue=venue, guide=guide, slot=slot, sched=sched,
                op=op, gu=gu)


BOOKER = dict(customer_name="Juan Dela Cruz", contact_phone="09171234567", contact_email="juan@example.com")


class FunctionalTests(TestCase):
    def setUp(self):
        self.w = make_world()
        self.c = APIClient()

    def register(self, username="camper1"):
        r = self.c.post("/api/auth/register/", {"username": username, "email": f"{username}@x.com",
                                                "password": "Strong-pass-2026", "first_name": "A",
                                                "last_name": "B"}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.c.credentials(HTTP_AUTHORIZATION=f"Token {r.data['token']}")
        return r

    def test_register_login_logout_and_password_is_hashed(self):
        self.register()
        u = User.objects.get(username="camper1")
        self.assertNotEqual(u.password, "Strong-pass-2026")
        self.assertTrue(u.password.startswith("pbkdf2_"))
        self.assertEqual(u.profile.role, Role.CAMPER)
        self.c.credentials()
        r = self.c.post("/api/auth/login/", {"username": "camper1", "password": "Strong-pass-2026"}, format="json")
        self.assertEqual(r.status_code, 200)
        bad = self.c.post("/api/auth/login/", {"username": "camper1", "password": "nope"}, format="json")
        self.assertEqual(bad.status_code, 400)
        self.c.credentials(HTTP_AUTHORIZATION=f"Token {r.data['token']}")
        self.assertEqual(self.c.post("/api/auth/logout/").status_code, 204)
        self.assertEqual(self.c.get("/api/auth/me/").status_code, 401)

    def test_catalog_filters_search_and_details(self):
        r = self.c.get("/api/destinations/?category=MOUNTAIN")
        self.assertEqual([d["name"] for d in r.data], ["Test Mountain"])
        r = self.c.get("/api/destinations/?q=unverified")
        self.assertEqual(len(r.data), 1)
        r = self.c.get("/api/destinations/?municipality=Almeria")
        self.assertEqual(len(r.data), 2)
        d = self.c.get("/api/destinations/test-beach/")
        self.assertEqual(d.status_code, 200)
        self.assertTrue(d.data["is_bookable"])
        self.assertEqual(d.data["services"]["type"], "VENUE")
        self.assertFalse(self.c.get("/api/destinations/unverified-beach/").data["is_bookable"])

    def test_availability_endpoints_are_separate(self):
        b = self.c.get("/api/destinations/test-beach/availability/").data
        m = self.c.get("/api/destinations/test-mountain/availability/").data
        self.assertEqual(b["services"][0]["slots"][0]["venue"], self.w["venue"].id)
        self.assertEqual(m["services"][0]["slots"][0]["guide"], self.w["guide"].id)

    def test_beach_booking_price_and_conflict(self):
        self.register()
        r = self.c.post("/api/bookings/beach/", {"slot_id": self.w["slot"].id, "guests": 6, **BOOKER}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(Decimal(r.data["total_amount"]), Decimal("600.00"))  # 500 + 2 extra x 50
        self.register("camper2")
        r2 = self.c.post("/api/bookings/beach/", {"slot_id": self.w["slot"].id, "guests": 2, **BOOKER}, format="json")
        self.assertEqual(r2.status_code, 409)

    def test_mountain_booking(self):
        self.register()
        r = self.c.post("/api/bookings/mountain/", {"schedule_id": self.w["sched"].id, "participants": 3, **BOOKER},
                        format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(Decimal(r.data["total_amount"]), Decimal("1800.00"))
        self.assertEqual(r.data["type"], "MOUNTAIN")

    def test_booking_validation(self):
        self.register()
        r = self.c.post("/api/bookings/beach/", {"slot_id": self.w["slot"].id, "guests": 99, **BOOKER}, format="json")
        self.assertEqual(r.status_code, 400)
        r = self.c.post("/api/bookings/beach/", {"slot_id": self.w["slot"].id, "guests": 2,
                                                 **{**BOOKER, "contact_email": "not-an-email"}}, format="json")
        self.assertEqual(r.status_code, 400)
        # A guide schedule id must not be accepted by the beach endpoint (separate inventories).
        r = self.c.post("/api/bookings/beach/", {"slot_id": 999999, "guests": 2, **BOOKER}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_unverified_destination_cannot_be_enabled(self):
        d = self.w["closed"]
        d.booking_enabled = True
        with self.assertRaises(IntegrityError), transaction.atomic():
            d.save()

    def test_cancel_and_history(self):
        self.register()
        r = self.c.post("/api/bookings/beach/", {"slot_id": self.w["slot"].id, "guests": 2, **BOOKER}, format="json")
        c = self.c.post(f"/api/bookings/beach/{r.data['id']}/cancel/")
        self.assertEqual(c.status_code, 200)
        self.assertEqual(c.data["status"], "CANCELLED")
        self.assertEqual([h["to_status"] for h in c.data["history"]], ["PENDING", "CANCELLED"])
        # slot is free again after cancellation
        r2 = self.c.post("/api/bookings/beach/", {"slot_id": self.w["slot"].id, "guests": 2, **BOOKER}, format="json")
        self.assertEqual(r2.status_code, 201)
        mine = self.c.get("/api/bookings/mine/?status=PENDING")
        self.assertEqual(len(mine.data), 1)


class SecurityTests(TestCase):
    def setUp(self):
        self.w = make_world()
        self.c = APIClient()

    def login(self, user):
        self.c.force_authenticate(user)

    def test_anonymous_cannot_book(self):
        r = self.c.post("/api/bookings/beach/", {"slot_id": self.w["slot"].id, "guests": 2, **BOOKER}, format="json")
        self.assertEqual(r.status_code, 401)

    def test_camper_cannot_use_admin_or_operator_api(self):
        camper = User.objects.create_user("cc", password="Cc-pass-12345")
        self.login(camper)
        for url in ["/api/admin/users/", "/api/admin/stats/", "/api/admin/destinations/", "/api/operator/reservations/"]:
            self.assertEqual(self.c.get(url).status_code, 403, url)

    def test_user_cannot_cancel_someone_elses_booking(self):
        a = User.objects.create_user("aa", password="Aa-pass-12345")
        b = User.objects.create_user("bb", password="Bb-pass-12345")
        r = services.create_beach_reservation(user=a, slot_id=self.w["slot"].id, guests=2, **BOOKER)
        self.login(b)
        self.assertEqual(self.c.post(f"/api/bookings/beach/{r.id}/cancel/").status_code, 403)

    def test_operator_only_manages_own_venue(self):
        other_op = User.objects.create_user("op2", password="Op2-pass-12345")
        other_op.profile.role = Role.VENUE_OPERATOR
        other_op.profile.save()
        camper = User.objects.create_user("cx", password="Cx-pass-12345")
        r = services.create_beach_reservation(user=camper, slot_id=self.w["slot"].id, guests=2, **BOOKER)
        self.login(other_op)
        self.assertEqual(self.c.post(f"/api/operator/reservations/beach/{r.id}/status/", {"status": "APPROVED"},
                                     format="json").status_code, 404)
        self.login(self.w["op"])
        ok = self.c.post(f"/api/operator/reservations/beach/{r.id}/status/", {"status": "APPROVED"}, format="json")
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.data["status"], "APPROVED")

    def test_self_registration_cannot_choose_admin_role(self):
        r = self.c.post("/api/auth/register/", {"username": "sneaky", "email": "s@x.com", "password": "Strong-pass-2026",
                                                "first_name": "S", "last_name": "N", "role": "ADMIN"}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(User.objects.get(username="sneaky").profile.role, Role.CAMPER)

    def test_overlapping_slots_rejected_by_database(self):
        s = self.w["slot"]
        with self.assertRaises(IntegrityError), transaction.atomic():
            VenueSlot.objects.create(venue=s.venue, start_at=s.start_at + timedelta(hours=1),
                                     end_at=s.end_at + timedelta(hours=1))

    def test_duplicate_active_reservation_rejected_by_database(self):
        u = User.objects.create_user("dup", password="Dup-pass-12345")
        services.create_beach_reservation(user=u, slot_id=self.w["slot"].id, guests=2, **BOOKER)
        with self.assertRaises(IntegrityError), transaction.atomic():
            BeachReservation.objects.create(user=u, slot=self.w["slot"], guests=1, base_amount=1, total_amount=1,
                                            **BOOKER)


class ConcurrencyTests(TransactionTestCase):
    """N threads, N separate DB connections, one exclusive slot."""

    N = 12

    def _race(self, fn):
        barrier = threading.Barrier(self.N)
        results, lock = [], threading.Lock()

        def worker(i):
            try:
                barrier.wait()  # release all threads at the same instant
                t0 = time.perf_counter()
                try:
                    fn(i)
                    outcome = "success"
                except services.SlotUnavailable:
                    outcome = "conflict"
                except Exception as exc:  # noqa: BLE001
                    outcome = f"error:{exc!r}"
                with lock:
                    results.append((outcome, (time.perf_counter() - t0) * 1000))
            finally:
                connection.close()

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(self.N)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        return results

    def setUp(self):
        self.w = make_world()
        self.users = [User.objects.create_user(f"race{i}", password="Race-pass-12345") for i in range(self.N)]

    def _report(self, label, results):
        ok = sum(r[0] == "success" for r in results)
        conflicts = sum(r[0] == "conflict" for r in results)
        times = sorted(r[1] for r in results)
        print(f"\n[{label}] simultaneous={self.N} success={ok} conflict={conflicts} "
              f"errors={self.N - ok - conflicts} min={times[0]:.1f}ms max={times[-1]:.1f}ms")
        return ok, conflicts

    def test_simultaneous_beach_bookings_only_one_wins(self):
        slot_id = self.w["slot"].id
        res = self._race(lambda i: services.create_beach_reservation(user=self.users[i], slot_id=slot_id, guests=2,
                                                                     **BOOKER))
        ok, conflicts = self._report("beach", res)
        self.assertEqual(ok, 1)
        self.assertEqual(conflicts, self.N - 1)
        self.assertEqual(BeachReservation.objects.filter(slot_id=slot_id, status=BookingStatus.PENDING).count(), 1)

    def test_simultaneous_guide_bookings_only_one_wins(self):
        sid = self.w["sched"].id
        res = self._race(lambda i: services.create_guide_reservation(user=self.users[i], schedule_id=sid,
                                                                     participants=2, **BOOKER))
        ok, conflicts = self._report("mountain", res)
        self.assertEqual(ok, 1)
        self.assertEqual(conflicts, self.N - 1)
        self.assertEqual(GuideReservation.objects.filter(schedule_id=sid).count(), 1)


# --------------------------------------------------------------------------
# Real-time (WebSocket) tests — in-memory channel layer, no Redis needed.
# --------------------------------------------------------------------------
from channels.db import database_sync_to_async  # noqa: E402
from channels.testing import WebsocketCommunicator  # noqa: E402
from django.test import override_settings  # noqa: E402
from rest_framework.authtoken.models import Token  # noqa: E402

from config.asgi import application  # noqa: E402

ORIGIN = [(b"origin", b"http://localhost")]


@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
class RealtimeTests(TransactionTestCase):
    async def _socket(self):
        comm = WebsocketCommunicator(application, "/ws/live/", headers=ORIGIN)
        connected, _ = await comm.connect()
        self.assertTrue(connected)
        self.assertEqual((await comm.receive_json_from(timeout=3))["type"], "hello")
        return comm

    async def test_operator_approval_is_pushed_to_camper_instantly(self):
        w = await database_sync_to_async(make_world)()
        camper = await database_sync_to_async(User.objects.create_user)("rt", password="Rt-pass-12345")
        token = await database_sync_to_async(lambda: Token.objects.create(user=camper).key)()
        r = await database_sync_to_async(services.create_beach_reservation)(
            user=camper, slot_id=w["slot"].id, guests=2, **BOOKER)

        comm = await self._socket()
        await comm.send_json_to({"type": "auth", "token": token})
        self.assertEqual((await comm.receive_json_from(timeout=3))["type"], "auth.ok")

        t0 = time.perf_counter()
        await database_sync_to_async(services.change_status)(BeachReservation, r.pk, "APPROVED", actor=w["op"])
        msg = await comm.receive_json_from(timeout=3)
        print(f"\n[realtime] approval delivered in {(time.perf_counter() - t0) * 1000:.1f} ms")
        self.assertEqual(msg["type"], "reservation.status")
        self.assertEqual(msg["status"], "APPROVED")
        self.assertEqual(msg["reference"], r.reference)
        await comm.disconnect()

    async def test_invalid_token_gets_no_private_events(self):
        comm = await self._socket()
        await comm.send_json_to({"type": "auth", "token": "not-a-real-token"})
        self.assertEqual((await comm.receive_json_from(timeout=3))["type"], "auth.error")
        await comm.disconnect()

    async def test_destination_watchers_see_slot_taken(self):
        w = await database_sync_to_async(make_world)()
        u = await database_sync_to_async(User.objects.create_user)("rw", password="Rw-pass-12345")
        comm = await self._socket()
        await comm.send_json_to({"type": "watch", "destination": "test-beach"})
        self.assertEqual((await comm.receive_json_from(timeout=3))["type"], "watching")
        await database_sync_to_async(services.create_beach_reservation)(
            user=u, slot_id=w["slot"].id, guests=2, **BOOKER)
        msg = await comm.receive_json_from(timeout=3)
        self.assertEqual(msg["type"], "availability.changed")
        self.assertEqual(msg["slot_id"], w["slot"].id)
        self.assertFalse(msg["available"])
        await comm.disconnect()

    async def test_rolled_back_booking_is_not_broadcast(self):
        w = await database_sync_to_async(make_world)()
        a = await database_sync_to_async(User.objects.create_user)("ra", password="Ra-pass-12345")
        b = await database_sync_to_async(User.objects.create_user)("rb", password="Rb-pass-12345")
        await database_sync_to_async(services.create_beach_reservation)(
            user=a, slot_id=w["slot"].id, guests=2, **BOOKER)
        comm = await self._socket()
        await comm.send_json_to({"type": "watch", "destination": "test-beach"})
        await comm.receive_json_from(timeout=3)
        with self.assertRaises(services.SlotUnavailable):
            await database_sync_to_async(services.create_beach_reservation)(
                user=b, slot_id=w["slot"].id, guests=2, **BOOKER)
        self.assertTrue(await comm.receive_nothing(timeout=0.5))  # conflict -> nothing pushed
        await comm.disconnect()
