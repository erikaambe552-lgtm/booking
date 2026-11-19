-- Database-layer concurrency test for CampBlazer.
-- Mirrors the tables/constraints Django creates for bookings (same names), so the
-- synchronization mechanism can be tested directly in PostgreSQL.
DROP SCHEMA IF EXISTS cb CASCADE;
CREATE SCHEMA cb;
SET search_path = cb;
CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE bookings_venueslot (
  id bigserial PRIMARY KEY,
  venue_id bigint NOT NULL,
  start_at timestamptz NOT NULL,
  end_at timestamptz NOT NULL,
  is_open boolean NOT NULL DEFAULT true,
  CONSTRAINT venueslot_end_after_start CHECK (end_at > start_at),
  CONSTRAINT venueslot_no_overlap EXCLUDE USING gist (tstzrange(start_at, end_at) WITH &&, venue_id WITH =)
);

CREATE TABLE bookings_guideschedule (
  id bigserial PRIMARY KEY,
  guide_id bigint NOT NULL,
  start_at timestamptz NOT NULL,
  end_at timestamptz NOT NULL,
  is_open boolean NOT NULL DEFAULT true,
  CONSTRAINT guideschedule_no_overlap EXCLUDE USING gist (tstzrange(start_at, end_at) WITH &&, guide_id WITH =)
);

CREATE TABLE bookings_beachreservation (
  id bigserial PRIMARY KEY,
  slot_id bigint NOT NULL REFERENCES bookings_venueslot(id),
  user_id int NOT NULL,
  status varchar(10) NOT NULL DEFAULT 'PENDING',
  created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
-- Partial unique index = "one ACTIVE reservation per slot"
CREATE UNIQUE INDEX one_active_reservation_per_venue_slot
  ON bookings_beachreservation (slot_id) WHERE status IN ('PENDING', 'APPROVED');

CREATE TABLE bookings_guidereservation (
  id bigserial PRIMARY KEY,
  schedule_id bigint NOT NULL REFERENCES bookings_guideschedule(id),
  user_id int NOT NULL,
  status varchar(10) NOT NULL DEFAULT 'PENDING',
  created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE UNIQUE INDEX one_active_reservation_per_guide_schedule
  ON bookings_guidereservation (schedule_id) WHERE status IN ('PENDING', 'APPROVED');

-- Control table WITHOUT the unique index: used only to show what goes wrong
-- when there is no synchronization at all.
CREATE TABLE naive_beachreservation (LIKE bookings_beachreservation INCLUDING DEFAULTS);

-- The booking transaction, same steps as bookings/services.py:
--   lock slot row (optional) -> re-check availability -> [processing] -> insert
-- mode: 'locked'          = SELECT ... FOR UPDATE + unique index   (CampBlazer design)
--       'constraint_only' = no lock, unique index only
--       'none'            = no lock, no unique index                (unsafe baseline)
CREATE FUNCTION try_book(p_kind text, p_slot bigint, p_user int, p_delay_ms int, p_mode text)
RETURNS text LANGUAGE plpgsql AS $$
DECLARE
  t0 timestamptz := clock_timestamp();
  t_lock timestamptz;
  taken boolean;
BEGIN
  IF p_mode = 'locked' THEN
    IF p_kind = 'beach' THEN
      PERFORM 1 FROM bookings_venueslot WHERE id = p_slot FOR UPDATE;
    ELSE
      PERFORM 1 FROM bookings_guideschedule WHERE id = p_slot FOR UPDATE;
    END IF;
  END IF;
  t_lock := clock_timestamp();

  IF p_kind = 'beach' AND p_mode = 'none' THEN
    SELECT EXISTS(SELECT 1 FROM naive_beachreservation WHERE slot_id = p_slot AND status IN ('PENDING','APPROVED')) INTO taken;
  ELSIF p_kind = 'beach' THEN
    SELECT EXISTS(SELECT 1 FROM bookings_beachreservation WHERE slot_id = p_slot AND status IN ('PENDING','APPROVED')) INTO taken;
  ELSE
    SELECT EXISTS(SELECT 1 FROM bookings_guidereservation WHERE schedule_id = p_slot AND status IN ('PENDING','APPROVED')) INTO taken;
  END IF;

  IF taken THEN
    RETURN format('conflict|%s|%s|%s', pg_backend_pid(),
                  round(extract(epoch FROM t_lock - t0)::numeric * 1000, 2),
                  round(extract(epoch FROM clock_timestamp() - t0)::numeric * 1000, 2));
  END IF;

  PERFORM pg_sleep(p_delay_ms / 1000.0);   -- simulated request-processing work inside the critical section

  IF p_kind = 'beach' AND p_mode = 'none' THEN
    INSERT INTO naive_beachreservation (slot_id, user_id) VALUES (p_slot, p_user);
  ELSIF p_kind = 'beach' THEN
    INSERT INTO bookings_beachreservation (slot_id, user_id) VALUES (p_slot, p_user);
  ELSE
    INSERT INTO bookings_guidereservation (schedule_id, user_id) VALUES (p_slot, p_user);
  END IF;

  RETURN format('success|%s|%s|%s', pg_backend_pid(),
                round(extract(epoch FROM t_lock - t0)::numeric * 1000, 2),
                round(extract(epoch FROM clock_timestamp() - t0)::numeric * 1000, 2));
EXCEPTION WHEN unique_violation THEN
  RETURN format('conflict_by_constraint|%s|%s|%s', pg_backend_pid(),
                round(extract(epoch FROM t_lock - t0)::numeric * 1000, 2),
                round(extract(epoch FROM clock_timestamp() - t0)::numeric * 1000, 2));
END $$;
