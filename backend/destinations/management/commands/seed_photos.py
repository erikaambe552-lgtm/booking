"""Attach photos to the 18 approved destinations.

1. Team-supplied photos in backend/seed_photos/, mapped by seed_photos/photos.json
   (credit taken from the visible watermark; all marked permission pending).
2. One freely-licensed Wikimedia Commons photo (extra Agta gallery image).

    python manage.py seed_photos            # add missing photos
    python manage.py seed_photos --reset    # REPLACE: delete all photos, then re-add from photos.json
                                            # (use this after updating to a new photo set)

Free hosting (Render etc.) wipes uploaded files on every restart. There, set
PHOTO_BASE_URL to the deployed FRONTEND address; the photos are then served by
the frontend (copied into frontend/public/photos at build time) and stored as
links instead of uploads:

    PHOTO_BASE_URL=https://campblazer.onrender.com python manage.py seed_photos
"""
import json
import os
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from destinations.models import Destination, DestinationImage

PHOTO_DIR = Path(__file__).resolve().parents[3] / "seed_photos"
PENDING = "Permission pending — confirm with owner before public launch"
FP = "https://commons.wikimedia.org/wiki/Special:FilePath/{}?width=1600"
PAGE = "https://commons.wikimedia.org/wiki/File:{}"

COMMONS = [
    dict(destination="Agta Beach Resort", file="Sunset_Agta_Beach_Resort_-_Biliran_Philippines.jpg",
         caption="Sunset at Agta Beach Resort (2007)", credit="Leodb / Wikimedia Commons",
         license="CC BY-SA / GFDL 1.2+"),
]


class Command(BaseCommand):
    help = "Attach photos to the approved destinations."

    def add_arguments(self, p):
        p.add_argument("--reset", action="store_true", help="Delete all destination photos first.")

    def handle(self, *args, reset, **kw):
        if reset:
            for img in DestinationImage.objects.all():
                if img.image_file:
                    img.image_file.delete(save=False)
                img.delete()
        manifest = json.loads((PHOTO_DIR / "photos.json").read_text(encoding="utf-8"))["photos"]
        added = 0
        for p in manifest:
            d = Destination.objects.filter(name=p["destination"]).first()
            if not d:
                raise CommandError(f"photos.json: destination '{p['destination']}' is not in the approved catalog.")
            if d.images.filter(caption=p["caption"]).exists():
                continue
            base = os.getenv("PHOTO_BASE_URL", "").rstrip("/")
            if base:  # link mode: no file stored on the server's disk
                DestinationImage.objects.create(
                    destination=d, image_url=f"{base}/photos/{p['file']}", caption=p["caption"], credit=p["credit"],
                    license=PENDING, is_cover=p.get("cover", False), order=0 if p.get("cover") else 1)
                added += 1
                continue
            with (PHOTO_DIR / p["file"]).open("rb") as fh:
                img = DestinationImage(destination=d, caption=p["caption"], credit=p["credit"], license=PENDING,
                                       is_cover=p.get("cover", False), order=0 if p.get("cover") else 1)
                img.image_file.save(p["file"], File(fh, name=p["file"]), save=True)
            added += 1
        for p in COMMONS:
            d = Destination.objects.get(name=p["destination"])
            _, created = DestinationImage.objects.get_or_create(
                destination=d, image_url=FP.format(p["file"]),
                defaults=dict(caption=p["caption"], credit=p["credit"], license=p["license"],
                              source_page=PAGE.format(p["file"]), is_cover=False, order=2))
            added += created
        missing = Destination.objects.filter(images__isnull=True).values_list("name", flat=True)
        self.stdout.write(self.style.SUCCESS(f"Added {added} photos."))
        if missing:
            self.stdout.write(self.style.WARNING("Still without a photo: " + ", ".join(missing)))
