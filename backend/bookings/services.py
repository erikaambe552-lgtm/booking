"""Reservation processing — the synchronization core of CampBlazer.

How two (or twenty) simultaneous requests for the SAME slot are resolved
---------------------------------------------------------------------------
Every request runs in a different server worker (gunicorn process or waitress
thread) with its OWN database connection. Inside `create_*_reservation`:

  1. `transaction.atomic()` opens a database transaction.
  2. `select_for_update()` takes a row-level lock on the slot row
     (SELECT ... FOR UPDATE). The first transaction to acquire it proceeds;
     every other transaction trying to lock the same row WAITS inside
     PostgreSQL — not in Python — until the holder commits or rolls back.
  3. While holding the lock, the worker re-checks availability against the
     database (the single source of truth), inserts the reservation, writes a
     history row and commits. Commit releases the lock.
  4. The next waiting transaction now acquires the lock, re-reads the slot,
     sees the active reservation and raises SlotUnavailable -> HTTP 409.

Which request wins is decided by lock acquisition order in PostgreSQL, NOT by
who clicked first in the browser. A partial UNIQUE index on
(slot) WHERE status IN ('PENDING','APPROVED') is a second, independent
safety net: a duplicate INSERT raises IntegrityError, also mapped to 409.
"""
import logging
import os
import time
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from . import realtime

from .models import (ACTIVE_STATUSES, BeachReservation, BookingHistory, BookingStatus, GuideReservation,
                     GuideSchedule, VenueSlot)

log = logging.getLogger("bookings")

# Optional artificial work inside the critical section, ONLY for classroom
# demos (makes lock waiting visible). Default 0 = off.
DEMO_DELAY_MS = int(os.getenv("BOOKING_DEMO_DELAY_MS", "0"))


class BookingError(Exception):
    http_status = 400
    code = "booking_error"


class SlotUnavailable(BookingError):
    http_status = 409
    code = "slot_unavailable"


class NotBookable(BookingError):
    http_status = 400
    code = "not_bookable"


def _demo_delay():
    if DEMO_DELAY_MS:
        time.sleep(DEMO_DELAY_MS / 1000)


def beach_price(venue, guests):
    base = Decimal(venue.base_price)
    extra_guests = max(0, guests - venue.included_guests)
    extra = Decimal(venue.price_per_extra_guest) * extra_guests
    return base, extra, base + extra


def guide_price(guide, participants):
    base = Decimal(guide.price_per_group)
    extra = Decimal(guide.price_per_participant) * participants
    return base, extra, base + extra


# --------------------------------------------------------------------------
# BEACHES — venue booking
# --------------------------------------------------------------------------
def create_beach_reservation(*, user, slot_id, guests, customer_name, contact_phone, contact_email,
                             special_requests=""):
    t0 = time.perf_counter()
    try:
        with transaction.atomic():
            # ---- critical section starts: row lock on the shared resource ----
            try:
                slot = (VenueSlot.objects.select_for_update()
                        .select_related("venue__destination").get(pk=slot_id))
            except VenueSlot.DoesNotExist:
                raise NotBookable("Slot not found.")
            venue = slot.venue
            dest = venue.destination

            if not (dest.is_published and dest.is_verified and dest.booking_enabled):
                raise NotBookable("This beach is not accepting online reservations yet.")
            if not (venue.is_active and venue.is_verified):
                raise NotBookable("This venue is not available for booking.")
            if not slot.is_open:
                raise SlotUnavailable("This slot has been closed by the operator.")
            if slot.start_at <= timezone.now():
                raise NotBookable("This slot is in the past.")
            if guests < 1 or guests > venue.max_guests:
                raise NotBookable(f"Guests must be between 1 and {venue.max_guests}.")

            # Re-check availability while holding the lock.
            if slot.reservations.filter(status__in=ACTIVE_STATUSES).exists():
                raise SlotUnavailable("Sorry — this venue slot was just reserved by another camper.")

            _demo_delay()
            base, extra, total = beach_price(venue, guests)
            r = BeachReservation.objects.create(
                user=user, slot=slot, guests=guests, customer_name=customer_name,
                contact_phone=contact_phone, contact_email=contact_email,
                special_requests=special_requests, base_amount=base, extra_amount=extra, total_amount=total,
            )
            BookingHistory.objects.create(beach_reservation=r, to_status=BookingStatus.PENDING,
                                          changed_by=user, note="Reservation submitted")
            realtime.reservation_created(r)  # pushed to browsers only after COMMIT
            # ---- commit releases the lock ----
    except IntegrityError:
        # Safety net: the partial unique index rejected a duplicate active booking.
        raise SlotUnavailable("Sorry — this venue slot was just reserved by another camper.")
    log.info("beach reservation %s slot=%s pid=%s %.1fms", r.reference, slot_id, os.getpid(),
             (time.perf_counter() - t0) * 1000)
    return r


# --------------------------------------------------------------------------
# MOUNTAINS — tour-guide booking
# --------------------------------------------------------------------------
def create_guide_reservation(*, user, schedule_id, participants, customer_name, contact_phone, contact_email,
                             special_requests=""):
    t0 = time.perf_counter()
    try:
        with transaction.atomic():
            try:
                schedule = (GuideSchedule.objects.select_for_update()
                            .select_related("guide__destination").get(pk=schedule_id))
            except GuideSchedule.DoesNotExist:
                raise NotBookable("Tour schedule not found.")
            guide = schedule.guide
            dest = guide.destination

            if not (dest.is_published and dest.is_verified and dest.booking_enabled):
                raise NotBookable("This mountain is not accepting guided-tour bookings yet.")
            if not (guide.is_active and guide.is_verified):
                raise NotBookable("This tour guide is not available for booking.")
            if not schedule.is_open:
                raise SlotUnavailable("This tour schedule has been closed by the guide.")
            if schedule.start_at <= timezone.now():
                raise NotBookable("This tour schedule is in the past.")
            if participants < 1 or participants > guide.max_participants:
                raise NotBookable(f"Participants must be between 1 and {guide.max_participants}.")

            if schedule.reservations.filter(status__in=ACTIVE_STATUSES).exists():
                raise SlotUnavailable("Sorry — this guide was just booked for that schedule.")

            _demo_delay()
            base, extra, total = guide_price(guide, participants)
            r = GuideReservation.objects.create(
                user=user, schedule=schedule, participants=participants, customer_name=customer_name,
                contact_phone=contact_phone, contact_email=contact_email,
                special_requests=special_requests, base_amount=base, extra_amount=extra, total_amount=total,
            )
            BookingHistory.objects.create(guide_reservation=r, to_status=BookingStatus.PENDING,
                                          changed_by=user, note="Reservation submitted")
            realtime.reservation_created(r)
    except IntegrityError:
        raise SlotUnavailable("Sorry — this guide was just booked for that schedule.")
    log.info("guide reservation %s schedule=%s pid=%s %.1fms", r.reference, schedule_id, os.getpid(),
             (time.perf_counter() - t0) * 1000)
    return r


# --------------------------------------------------------------------------
# Status changes (cancel / approve / reject / complete)
# --------------------------------------------------------------------------
ALLOWED_TRANSITIONS = {
    BookingStatus.PENDING: {BookingStatus.APPROVED, BookingStatus.REJECTED, BookingStatus.CANCELLED},
    BookingStatus.APPROVED: {BookingStatus.CANCELLED, BookingStatus.COMPLETED},
    BookingStatus.REJECTED: set(),
    BookingStatus.CANCELLED: set(),
    BookingStatus.COMPLETED: set(),
}


def change_status(model, pk, new_status, *, actor, note=""):
    """Lock the reservation row, validate the transition, update, audit."""
    with transaction.atomic():
        r = model.objects.select_for_update().get(pk=pk)
        if new_status not in ALLOWED_TRANSITIONS[r.status]:
            raise BookingError(f"Cannot change a {r.status.lower()} reservation to {new_status.lower()}.")
        old = r.status
        r.status = new_status
        r.save(update_fields=["status", "updated_at"])
        kw = {"beach_reservation": r} if model is BeachReservation else {"guide_reservation": r}
        BookingHistory.objects.create(from_status=old, to_status=new_status, changed_by=actor, note=note, **kw)
        # e.g. operator APPROVES -> the camper's open browser tab is updated instantly via WebSocket
        realtime.status_changed(r, old, new_status, note)
    return r


def start_of(reservation):
    return reservation.slot.start_at if isinstance(reservation, BeachReservation) else reservation.schedule.start_at


def can_user_cancel(reservation):
    return reservation.status in ACTIVE_STATUSES and start_of(reservation) > timezone.now()
