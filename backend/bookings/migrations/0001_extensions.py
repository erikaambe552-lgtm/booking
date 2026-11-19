"""Enables btree_gist, required by the ExclusionConstraints that stop a venue or
guide from having overlapping time slots. `makemigrations` will create
0002_initial depending on this migration."""
from django.contrib.postgres.operations import BtreeGistExtension
from django.db import migrations


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [BtreeGistExtension()]
