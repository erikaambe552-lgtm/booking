"""Bulk-import the team's own (or permission-granted) destination photos.

Folder layout (one sub-folder per destination slug):

    photos/
      credits.csv
      higatangan-island/sandbar.jpg
      sambawan-island/viewdeck.jpg
      mount-tres-marias/summit.jpg

credits.csv columns:  slug,filename,credit,license,caption,is_cover
    higatangan-island,sandbar.jpg,Photo by J. Dela Cruz (BiPSU),Own photo,Higatangan shifting sandbar,1

Every photo MUST have a row with a credit — files without one are skipped.

    python manage.py import_photos ../photos
"""
import csv
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from destinations.models import Destination, DestinationImage, validate_image_file


class Command(BaseCommand):
    help = "Import destination photos from a folder with credits.csv"

    def add_arguments(self, p):
        p.add_argument("folder")

    def handle(self, *args, folder, **kw):
        root = Path(folder)
        credits = root / "credits.csv"
        if not credits.exists():
            raise CommandError(f"{credits} not found — every photo needs a credit row.")
        done = skipped = 0
        with credits.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                path = root / row["slug"] / row["filename"]
                dest = Destination.objects.filter(slug=row["slug"]).first()
                if not dest or not path.exists() or not row.get("credit", "").strip():
                    self.stdout.write(self.style.WARNING(f"skip {path} (missing destination, file or credit)"))
                    skipped += 1
                    continue
                with path.open("rb") as f:
                    django_file = File(f, name=path.name)
                    validate_image_file(django_file)
                    img = DestinationImage(destination=dest, credit=row["credit"].strip(),
                                           license=row.get("license", "").strip(),
                                           caption=row.get("caption", "").strip(),
                                           is_cover=row.get("is_cover", "").strip() in ("1", "true", "yes"))
                    img.image_file.save(f"{dest.slug}-{path.name}", django_file, save=True)
                done += 1
        self.stdout.write(self.style.SUCCESS(f"Imported {done} photos, skipped {skipped}."))
