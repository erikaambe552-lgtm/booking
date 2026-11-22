from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
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
            """,
            reverse_sql="DROP TRIGGER IF EXISTS core_venueslot_no_overlap_insert;",
        ),
        migrations.RunSQL(
            sql="""
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
            """,
            reverse_sql="DROP TRIGGER IF EXISTS core_venueslot_no_overlap_update;",
        ),
        migrations.RunSQL(
            sql="""
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
            """,
            reverse_sql="DROP TRIGGER IF EXISTS core_guideschedule_no_overlap_insert;",
        ),
        migrations.RunSQL(
            sql="""
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
            """,
            reverse_sql="DROP TRIGGER IF EXISTS core_guideschedule_no_overlap_update;",
        ),
    ]
