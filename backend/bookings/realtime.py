"""Server -> browser push over WebSockets (Django Channels + Redis).

Events are published with transaction.on_commit, so browsers are only told
about changes that are actually committed in PostgreSQL — never about a
booking that was rolled back. If Redis is unavailable the booking still
succeeds; the event is logged and skipped (the UI also refreshes on load).

Groups
  user_<id>      a camper's own reservation updates
  provider_<id>  an operator/guide: new bookings for their services
  admins         all administrators
  dest_<slug>    anyone viewing a destination page: live availability
"""
import logging
import os

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.utils import timezone

log = logging.getLogger("bookings")
ACTIVE = ("PENDING", "APPROVED")


def _send(group, payload):
    layer = get_channel_layer()
    if layer is None:
        return
    payload = {**payload, "published_by_pid": os.getpid(), "published_at": timezone.now().isoformat()}
    try:
        async_to_sync(layer.group_send)(group, {"type": "push", "payload": payload})
    except Exception as exc:  # Redis down etc. — never break the booking itself
        log.warning("realtime publish to %s failed: %r", group, exc)


def publish(group, payload):
    transaction.on_commit(lambda: _send(group, payload))


def _describe(r):
    from .models import BeachReservation
    if isinstance(r, BeachReservation):
        res, kind, owner_id = r.slot, "beach", r.slot.venue.operator_id
        dest, service = r.slot.venue.destination, r.slot.venue.name
    else:
        res, kind, owner_id = r.schedule, "mountain", r.schedule.guide.user_id
        dest, service = r.schedule.guide.destination, r.schedule.guide.display_name
    return res, kind, owner_id, dest, service


def availability_changed(dest_slug, kind, slot_id, available):
    publish(f"dest_{dest_slug}", {"type": "availability.changed", "destination": dest_slug, "kind": kind,
                                  "slot_id": slot_id, "available": available})


def reservation_created(r):
    res, kind, owner_id, dest, service = _describe(r)
    info = {"id": r.id, "kind": kind, "reference": r.reference, "status": r.status, "destination": dest.name,
            "service": service, "start_at": res.start_at.isoformat(), "customer_name": r.customer_name}
    availability_changed(dest.slug, kind, res.id, False)
    if owner_id:
        publish(f"provider_{owner_id}", {"type": "reservation.new", **info})
    publish("admins", {"type": "reservation.new", **info})


def status_changed(r, old, new, note=""):
    res, kind, owner_id, dest, service = _describe(r)
    info = {"id": r.id, "kind": kind, "reference": r.reference, "status": new, "old_status": old,
            "destination": dest.name, "service": service, "note": note}
    publish(f"user_{r.user_id}", {"type": "reservation.status", **info})
    if owner_id:
        publish(f"provider_{owner_id}", {"type": "reservation.status", **info})
    publish("admins", {"type": "reservation.status", **info})
    if old in ACTIVE and new not in ACTIVE:  # slot released (cancelled / rejected)
        availability_changed(dest.slug, kind, res.id, res.is_open and res.start_at > timezone.now())


def slot_changed(slot, kind):
    """Operator opened/closed/created a slot."""
    dest = slot.venue.destination if kind == "beach" else slot.guide.destination
    taken = slot.reservations.filter(status__in=ACTIVE).exists() if slot.pk else False
    availability_changed(dest.slug, kind, slot.id, slot.is_open and not taken)
