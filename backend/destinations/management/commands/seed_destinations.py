"""Seed the APPROVED Biliran-only catalog: 12 beaches + 6 mountains (18 destinations).

The final approved list (Agta Beach Resort appeared twice in the list, so it is
stored once). Any destination NOT on this list is deleted from the database,
together with its photos, venues/guides, slots and reservations.

All approved destinations are marked verified with booking ENABLED. A booking
button becomes active as soon as the destination has a verified venue (beach)
or tour guide (mountain) with open slots — added by an admin/operator, or by
`python manage.py seed_demo` for the capstone demonstration.

Location fields are filled only where a source was found (see source_notes);
otherwise location_verified=False and the admin must confirm them.

    python manage.py seed_destinations
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from bookings.models import BeachReservation, GuideReservation
from destinations.models import Destination

BEACHES = [{'name': 'VRC Beach Resort',
  'municipality': 'Almeria',
  'barangay': 'Talahid',
  'location_verified': True,
  'short_description': 'Beach resort on the Talahid beach strip in Almeria.',
  'source_notes': "biliran.gov.ph (Provincial Government of Biliran tourism pages) 'Talahid Beach Area' and 'VRC "
                  "Resort'.",
  'is_featured': True},
 {'name': 'Paradizu Bayview Resort',
  'municipality': 'Almeria',
  'barangay': 'Talahid',
  'location_verified': True,
  'short_description': 'Talahid-strip resort with a function hall, pool and beach cottages.',
  'amenities': ['Function hall', 'Swimming pool', 'Air-conditioned rooms', 'Beach cottages', 'Karaoke'],
  'source_notes': "biliran.gov.ph (Provincial Government of Biliran tourism pages) 'Paradizu Bayview Resort' "
                  '(amenities as listed there; confirm with operator).',
  'is_featured': True},
 {'name': 'Coco Grove Beach Resort',
  'municipality': 'Almeria',
  'barangay': 'Talahid',
  'location_verified': True,
  'short_description': 'Beach resort on the Talahid beach strip in Almeria.',
  'source_notes': "biliran.gov.ph (Provincial Government of Biliran tourism pages) 'Talahid Beach Area'.",
  'is_featured': True},
 {'name': 'Agta Beach Resort',
  'municipality': 'Almeria',
  'barangay': 'Talahid',
  'location_verified': True,
  'is_featured': True,
  'short_description': 'Long-running beach resort on the Talahid strip in Almeria, popular with divers and as a base '
                       'for island trips.',
  'description': 'Agta Beach Resort sits on the Talahid beach strip in Almeria. Travel guides describe it as a base '
                 'for dive and boat trips to nearby islands such as Dalutan.',
  'activities': ['Swimming', 'Diving trips', 'Island hopping'],
  'source_notes': 'biliran.gov.ph (Provincial Government of Biliran tourism pages); Lonely Planet; Vigattin Tourism '
                  '(Almeria, ~30 min from Naval).'},
 {'name': 'Higatangan Island',
  'municipality': 'Naval',
  'location_verified': True,
  'is_featured': True,
  'short_description': "Naval's island village famous for its shifting white sandbar, rock formations and quiet "
                       'beaches.',
  'description': 'Higatangan is an island under the municipality of Naval with two barangays. It is best known for a '
                 'white sandbar whose shape and position shift with the wind and currents, plus rock formations, a '
                 'lighthouse and quiet beaches. Access is by boat from Naval port.',
  'activities': ['Sandbar visit', 'Swimming', 'Island walk', 'Photography'],
  'source_notes': 'biliran.gov.ph (Provincial Government of Biliran tourism pages) (coordinates 11°34\'7.62"N '
                  '124°15\'50.85"E); Philippine News Agency 2024; Inquirer \'Isle of shifting sandbars revisited\'.'},
 {'name': 'Dalutan Island',
  'municipality': 'Almeria',
  'location_verified': True,
  'is_featured': True,
  'short_description': 'A small island a short boat ride from Agta Beach with a strip of white sand and good '
                       'snorkelling.',
  'description': 'Dalutan is a small island in Almeria reached by a short pump-boat ride from the Agta/Talahid beach '
                 'area. It has a stretch of white sand along an otherwise rocky shore.',
  'activities': ['Island hopping', 'Snorkelling', 'Swimming'],
  'source_notes': 'touristspotsfinder (Almeria); Vigattin Tourism; Lonely Planet (Agta Beach as base).'},
 {'name': 'Chamorita Beach Resort',
  'municipality': 'Naval',
  'barangay': 'Catmon',
  'location_verified': True,
  'short_description': 'Popular west-coast resort just south of Naval town, with a family pool and slides, local '
                       'dining and sunset views.',
  'source_notes': "biliran.gov.ph (Provincial Government of Biliran tourism pages) 'Chamorita Beach Resort' — "
                  'address Brgy. Catmon, Naval.',
  'is_featured': True},
 {'name': 'Napo Beach Resort',
  'municipality': 'Maripipi',
  'barangay': 'Viga (Sitio Napo)',
  'location_verified': True,
  'short_description': 'Island getaway on Maripipi with rooms, a seaside pool and a jetty over clear water; runs '
                       'trips to Sambawan.',
  'source_notes': "biliran.gov.ph (Provincial Government of Biliran tourism pages) 'Napo Beach Resort' (Brgy. Viga, "
                  'Maripipi); Lonely Planet (runs Sambawan trips).',
  'is_featured': True},
 {'name': 'Agpangi Brown Beach',
  'municipality': 'Naval',
  'barangay': 'Agpangi',
  'location_verified': True,
  'short_description': 'A quiet stretch of brown, sometimes golden, sand in Brgy. Agpangi with views toward Mount '
                       'Panamao.',
  'activities': ['Swimming', 'Sunset viewing'],
  'source_notes': 'PhilAtlas (Agpangi is a barangay of Naval); beachatlas / Sandee listings (Naval).',
  'is_featured': True},
 {'name': 'Cogon Beach Resort',
  'municipality': 'Kawayan',
  'location_verified': False,
  'location_note': 'Cogon Beach is listed in Kawayan (about 30 min by motorboat from the town proper); confirm the '
                   "resort's exact barangay.",
  'short_description': 'Beach in Kawayan noted for white coral sand, diving and nearby Tingkasan bat cave.',
  'activities': ['Swimming', 'Diving', 'Island hopping'],
  'source_notes': "Vigattin Tourism 'Cogon Beach — Kawayan, Biliran'.",
  'is_featured': True},
 {'name': 'Alegre Beach Resort',
  'location_verified': False,
  'location_note': 'No published Biliran address found yet — admin must confirm the municipality.',
  'short_description': 'Beachfront resort with shaded cottages and kayaks; details awaiting verification.',
  'source_notes': 'Team-provided listing; no external source confirmed yet.',
  'is_featured': True},
 {'name': "Francis' Place",
  'location_verified': False,
  'location_note': 'No published Biliran address found yet — admin must confirm the municipality.',
  'short_description': 'Seaside spot with a floating cottage and beachfront rooms; details awaiting verification.',
  'source_notes': 'Team-provided listing; no external source confirmed yet.',
  'is_featured': True}]

MOUNTAINS = [{'name': 'Mount Tres Marias',
  'municipality': 'Almeria',
  'location_verified': True,
  'is_featured': True,
  'location_note': 'Mountain range; standard jump-off is Brgy. Sampao, Almeria.',
  'short_description': "Biliran's three-peaked range with mossy forest, waterfalls and stream crossings — an "
                       'overnight major climb.',
  'description': "Tres Marias is a range of three peaks; its highest point is also Biliran's highest. Hikers "
                 'describe mossy forest, waterfalls and stream crossings. The usual climb is overnight from Brgy. '
                 'Sampao, Almeria, where trekkers register.',
  'activities': ['Overnight hike', 'Camping', 'Waterfalls'],
  'source_notes': "PinoyMountaineer 'Mt. Tres Marias'; gunungbagging; Climb Biliran (PNA)."},
 {'name': 'Mount Panamao',
  'location_verified': False,
  'is_featured': True,
  'location_note': 'Northernmost mountain of Biliran Island (inactive volcano). Municipality to be confirmed.',
  'short_description': 'An inactive volcanic cone at the northern tip of Biliran Island, promoted under Climb '
                       'Biliran.',
  'activities': ['Day hike'],
  'source_notes': "UP Resilience Institute volcano profile; PNA 'Climb Biliran'."},
 {'name': 'Mount Suiro (Ascuero)',
  'location_verified': True,
  'location_note': 'Jump-off at Sitio Ansay, Brgy. Union, Caibiran (Climb Biliran guides).',
  'short_description': 'Volcanic dome in south-eastern Biliran climbed from Caibiran with Climb Biliran guides.',
  'activities': ['Hike'],
  'source_notes': "advenature blog 2025 (jump-off Sitio Ansay, Brgy. Union, Caibiran); PNA 'Climb Biliran'.",
  'municipality': 'Caibiran',
  'is_featured': True},
 {'name': 'Mount Naliwatan',
  'municipality': 'Almeria',
  'location_verified': False,
  'is_featured': True,
  'location_note': 'Highest peak of the Tres Marias range. Usual jump-off: Brgy. Sampao, Almeria; some maps place '
                   'the summit within Kawayan — confirm municipal boundary.',
  'short_description': 'The highest summit of the Tres Marias range, known for mossy forest and a summit campsite.',
  'activities': ['Summit hike', 'Camping'],
  'source_notes': 'gunungbagging (1,346 m per PeakVisor; Tres Marias peak 3); mapcarta.'},
 {'name': 'Mount Sayoa',
  'location_verified': False,
  'location_note': 'Volcanic mountain seen from Caibiran in south-east Biliran. Municipality to be confirmed.',
  'short_description': 'Volcanic mountain overlooking the south-eastern corner of Biliran Island.',
  'source_notes': 'biliran.boards.net photo captions.',
  'is_featured': True},
 {'name': 'Camp Beben',
  'municipality': 'Kawayan',
  'location_verified': False,
  'is_featured': True,
  'location_note': 'Listed under Kawayan on the provincial tourism site (a short drive from Naval); the barangay is '
                   'not stated — confirm with the LGU.',
  'short_description': 'Open, elevated mountain campsite with grassland tent areas below a forested peak — known for '
                       'stargazing, sunrises and sunsets.',
  'description': 'Camp Beben is a mountain retreat promoted by the provincial tourism office. It keeps a mostly '
                 'natural setting with designated camping areas, picnic tables and restrooms; local guides can be '
                 'hired for the nearby trails. Bring your own camping essentials.',
  'amenities': ['Designated camping areas', 'Picnic tables', 'Restrooms'],
  'activities': ['Overnight camping', 'Trail hiking with local guides', 'Stargazing', 'Sunrise & sunset viewing'],
  'source_notes': "biliran.gov.ph 'Discover Camp Beben: A Mountain Retreat in Biliran' (tagged Kawayan)."}]

DEFAULT_BEACH_INSTRUCTIONS = ("Choose a venue or camping area, pick an open date slot, and submit. The operator "
                              "confirms your reservation; you'll see the status change live in My reservations.")
DEFAULT_MOUNTAIN_INSTRUCTIONS = ("Choose a date, an available tour guide and a schedule, then submit. Register with "
                                 "the barangay / LGU at the jump-off before hiking. Status updates appear live.")

APPROVED = [r["name"] for r in BEACHES + MOUNTAINS]


class Command(BaseCommand):
    help = "Sync the catalog to the 18 approved Biliran destinations (removes any others)."

    def add_arguments(self, p):
        p.add_argument("--keep-unapproved", action="store_true", help="Don't delete destinations outside the list.")

    @transaction.atomic
    def handle(self, *args, keep_unapproved=False, **opts):
        removed = []
        if not keep_unapproved:
            for d in Destination.objects.exclude(name__in=APPROVED):
                # Remove everything attached: reservations, slots/schedules, services, photos.
                BeachReservation.objects.filter(slot__venue__destination=d).delete()
                GuideReservation.objects.filter(schedule__guide__destination=d).delete()
                for img in d.images.all():
                    if img.image_file:
                        img.image_file.delete(save=False)
                removed.append(d.name)
                d.delete()  # cascades venues, guides, slots, schedules, images
        created = 0
        for cat, rows, instr in (("BEACH", BEACHES, DEFAULT_BEACH_INSTRUCTIONS),
                                 ("MOUNTAIN", MOUNTAINS, DEFAULT_MOUNTAIN_INSTRUCTIONS)):
            for row in rows:
                row = {**row}
                name = row.pop("name")
                row.setdefault("reservation_instructions", instr)
                _, was_created = Destination.objects.update_or_create(
                    name=name, defaults={"category": cat, "is_published": True, "is_verified": True,
                                         "booking_enabled": True, **row})
                created += was_created
        if removed:
            self.stdout.write(self.style.WARNING(f"Removed {len(removed)} unapproved: " + ", ".join(removed)))
        self.stdout.write(self.style.SUCCESS(
            f"Catalog synced: {len(BEACHES)} beaches + {len(MOUNTAINS)} mountains ({created} new). "
            f"Run `seed_photos`, then `seed_demo` to give every destination a bookable [DEMO] service."))
