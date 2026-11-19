"""Create SIMULATED accounts and services so EVERY approved destination can be
booked during the panel demonstration.

For each of the 18 approved destinations it creates exactly one clearly
labelled service — never a new destination:
  * beach    -> "[DEMO] Camping Area" (BeachVenue)  owned by operator_demo
  * mountain -> "[DEMO] Guide Team"   (MountainGuide) owned by guide_demo
plus 14 days of open slots / tour schedules.

Everything is flagged is_demo=True and shown with a "Simulated" badge, so it is
never mistaken for a real operator, guide or price. Replace with real services
in the Admin dashboard, then remove the demo with --remove.

    python manage.py seed_demo                 # create / top up
    python manage.py seed_demo --campers 20    # number of test camper accounts
    python manage.py seed_demo --remove        # delete all demo data
"""
import os
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import Role
from bookings.models import BeachReservation, GuideReservation, GuideSchedule, VenueSlot
from destinations.models import BeachVenue, Category, Destination, MountainGuide

VENUE_NAME = "[DEMO] Camping Area"
GUIDE_NAME = "[DEMO] Guide Team"
DAYS = 14


def _user(username, password, role, staff=False):
    u, created = User.objects.get_or_create(username=username, defaults={
        "email": f"{username}@demo.campblazer.test", "first_name": username.split("_")[0].title(),
        "last_name": "Demo", "is_staff": staff})
    if created:
        u.set_password(password)
        u.save()
    u.profile.role = role
    u.profile.save()
    return u


class Command(BaseCommand):
    help = "Give every approved destination one simulated [DEMO] venue or guide with open slots."

    def add_arguments(self, p):
        p.add_argument("--campers", type=int, default=20)
        p.add_argument("--remove", action="store_true")

    @transaction.atomic
    def handle(self, *args, campers, remove, **kw):
        if remove:
            BeachReservation.objects.filter(slot__venue__is_demo=True).delete()
            GuideReservation.objects.filter(schedule__guide__is_demo=True).delete()
            BeachVenue.objects.filter(is_demo=True).delete()
            MountainGuide.objects.filter(is_demo=True).delete()
            User.objects.filter(email__endswith="@demo.campblazer.test").delete()
            self.stdout.write(self.style.WARNING("Demo data removed. Booking buttons stay active only where a "
                                                 "real verified venue/guide exists."))
            return

        pw = os.getenv("DEMO_PASSWORD", "CampDemo#2026")
        _user("admin_demo", pw, Role.ADMIN, staff=True)
        operator = _user("operator_demo", pw, Role.VENUE_OPERATOR)
        guide_user = _user("guide_demo", pw, Role.GUIDE)
        for i in range(1, campers + 1):
            _user(f"camper{i:02d}_demo", pw, Role.CAMPER)

        tz = timezone.get_current_timezone()
        today = timezone.localdate()
        services = made = 0
        for d in Destination.objects.filter(is_published=True).order_by("category", "name"):
            if not (d.is_verified and d.booking_enabled):
                continue  # only destinations an admin has approved
            if d.category == Category.BEACH:
                venue, _ = BeachVenue.objects.update_or_create(destination=d, name=VENUE_NAME, defaults=dict(
                    operator=operator, max_guests=10, base_price=Decimal("500.00"), included_guests=4,
                    price_per_extra_guest=Decimal("50.00"),
                    description="SIMULATED camping area for the capstone demonstration. Not a real offer.",
                    is_verified=True, is_active=True, is_demo=True))
                for offset in range(1, DAYS + 1):
                    s = datetime.combine(today + timedelta(days=offset), time(8, 0), tz)
                    _, c = VenueSlot.objects.get_or_create(venue=venue, start_at=s, defaults=dict(
                        end_at=s + timedelta(hours=24), note="Overnight camping slot (demo)"))
                    made += c
            else:
                guide, _ = MountainGuide.objects.update_or_create(destination=d, display_name=GUIDE_NAME, defaults=dict(
                    user=guide_user, max_participants=8, price_per_group=Decimal("1500.00"),
                    price_per_participant=Decimal("100.00"),
                    bio="SIMULATED guide team for the capstone demonstration. Not a real guide.",
                    is_verified=True, is_active=True, is_demo=True))
                for offset in range(1, DAYS + 1):
                    g = datetime.combine(today + timedelta(days=offset), time(5, 0), tz)
                    _, c = GuideSchedule.objects.get_or_create(guide=guide, start_at=g, defaults=dict(
                        end_at=g + timedelta(hours=14), meeting_point="Jump-off registration point (demo)"))
                    made += c
            services += 1

        self.stdout.write(self.style.SUCCESS(
            f"Demo ready. Password for all demo accounts: {pw}\n"
            f"  admin_demo / operator_demo / guide_demo / camper01_demo..camper{campers:02d}_demo\n"
            f"  {services} destinations now bookable ([DEMO] services); {made} new slots/schedules."))
