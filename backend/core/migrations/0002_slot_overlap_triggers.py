from django.db import migrations


SQLITE_VENUE_INSERT = """
CREATE TRIGGER core_venueslot_no_overlap_insert
BEFORE INSERT ON core_venueslot
WHEN EXISTS (
    SELECT 1 FROM core_venueslot
    WHERE venue_id = NEW.venue_id
      AND start_at < NEW.end_at
      AND end_at > NEW.start_at
)
BEGIN
    SELECT RAISE(ABORT, 'venueslot_no_overlap');
END;
"""

SQLITE_VENUE_UPDATE = """
CREATE TRIGGER core_venueslot_no_overlap_update
BEFORE UPDATE ON core_venueslot
WHEN EXISTS (
    SELECT 1 FROM core_venueslot
    WHERE venue_id = NEW.venue_id
      AND id != OLD.id
      AND start_at < NEW.end_at
      AND end_at > NEW.start_at
)
BEGIN
    SELECT RAISE(ABORT, 'venueslot_no_overlap');
END;
"""

SQLITE_GUIDE_INSERT = """
CREATE TRIGGER core_guideschedule_no_overlap_insert
BEFORE INSERT ON core_guideschedule
WHEN EXISTS (
    SELECT 1 FROM core_guideschedule
    WHERE guide_id = NEW.guide_id
      AND start_at < NEW.end_at
      AND end_at > NEW.start_at
)
BEGIN
    SELECT RAISE(ABORT, 'guideschedule_no_overlap');
END;
"""

SQLITE_GUIDE_UPDATE = """
CREATE TRIGGER core_guideschedule_no_overlap_update
BEFORE UPDATE ON core_guideschedule
WHEN EXISTS (
    SELECT 1 FROM core_guideschedule
    WHERE guide_id = NEW.guide_id
      AND id != OLD.id
      AND start_at < NEW.end_at
      AND end_at > NEW.start_at
)
BEGIN
    SELECT RAISE(ABORT, 'guideschedule_no_overlap');
END;
"""


def create_overlap_guards(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute("""
            CREATE OR REPLACE FUNCTION core_venueslot_no_overlap_fn()
            RETURNS trigger AS $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM core_venueslot
                    WHERE venue_id = NEW.venue_id
                      AND id <> COALESCE(NEW.id, -1)
                      AND tstzrange(start_at, end_at, '[)')
                          && tstzrange(NEW.start_at, NEW.end_at, '[)')
                ) THEN
                    RAISE EXCEPTION 'venueslot_no_overlap';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
        schema_editor.execute("""
            CREATE TRIGGER core_venueslot_no_overlap_insert_update
            BEFORE INSERT OR UPDATE ON core_venueslot
            FOR EACH ROW EXECUTE FUNCTION core_venueslot_no_overlap_fn();
        """)
        schema_editor.execute("""
            CREATE OR REPLACE FUNCTION core_guideschedule_no_overlap_fn()
            RETURNS trigger AS $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM core_guideschedule
                    WHERE guide_id = NEW.guide_id
                      AND id <> COALESCE(NEW.id, -1)
                      AND tstzrange(start_at, end_at, '[)')
                          && tstzrange(NEW.start_at, NEW.end_at, '[)')
                ) THEN
                    RAISE EXCEPTION 'guideschedule_no_overlap';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
        schema_editor.execute("""
            CREATE TRIGGER core_guideschedule_no_overlap_insert_update
            BEFORE INSERT OR UPDATE ON core_guideschedule
            FOR EACH ROW EXECUTE FUNCTION core_guideschedule_no_overlap_fn();
        """)
        return

    for sql in (
        SQLITE_VENUE_INSERT,
        SQLITE_VENUE_UPDATE,
        SQLITE_GUIDE_INSERT,
        SQLITE_GUIDE_UPDATE,
    ):
        schema_editor.execute(sql)


def remove_overlap_guards(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(
            "DROP TRIGGER IF EXISTS core_venueslot_no_overlap_insert_update ON core_venueslot;"
        )
        schema_editor.execute("DROP FUNCTION IF EXISTS core_venueslot_no_overlap_fn();")
        schema_editor.execute(
            "DROP TRIGGER IF EXISTS core_guideschedule_no_overlap_insert_update ON core_guideschedule;"
        )
        schema_editor.execute("DROP FUNCTION IF EXISTS core_guideschedule_no_overlap_fn();")
        return

    for trigger in (
        "core_venueslot_no_overlap_insert",
        "core_venueslot_no_overlap_update",
        "core_guideschedule_no_overlap_insert",
        "core_guideschedule_no_overlap_update",
    ):
        schema_editor.execute(f"DROP TRIGGER IF EXISTS {trigger};")


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_overlap_guards, remove_overlap_guards),
    ]
