"""Fleet service initial migration — creates all owned tables."""
from django.db import migrations


class Migration(migrations.Migration):

    initial = True
    dependencies = []

    operations = [
        migrations.RunSQL(
            sql="""
            -- ── Cities ────────────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS cities (
                id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name       VARCHAR(100) NOT NULL,
                state      VARCHAR(100) NOT NULL,
                is_active  BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );

            -- ── Fleet Hubs ────────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS fleet_hubs (
                id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                city_id    UUID NOT NULL REFERENCES cities(id),
                name       VARCHAR(200) NOT NULL,
                address    TEXT NOT NULL,
                latitude   DECIMAL(10, 8),
                longitude  DECIMAL(11, 8),
                capacity   INTEGER NOT NULL DEFAULT 0,
                manager_id UUID,
                is_active  BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_fleet_hubs_city
                ON fleet_hubs(city_id) WHERE is_active = TRUE;

            -- ── Vehicles ──────────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS vehicles (
                id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                hub_id               UUID NOT NULL REFERENCES fleet_hubs(id),
                registration_number  VARCHAR(20)  NOT NULL UNIQUE,
                chassis_number       VARCHAR(50)  UNIQUE,
                motor_number         VARCHAR(50)  UNIQUE,
                make                 VARCHAR(100),
                model                VARCHAR(100),
                manufacturing_year   INTEGER,
                color                VARCHAR(50),
                battery_capacity_kwh DECIMAL(5,2),
                battery_health_pct   DECIMAL(5,2),
                range_km             INTEGER,
                max_speed_kmh        INTEGER,
                current_odometer_km  DECIMAL(10,2) NOT NULL DEFAULT 0,
                last_gps_lat         DECIMAL(10,8),
                last_gps_lng         DECIMAL(11,8),
                last_gps_at          TIMESTAMPTZ,
                battery_level_pct    DECIMAL(5,2),
                is_charging          BOOLEAN NOT NULL DEFAULT FALSE,
                status               VARCHAR(20) NOT NULL DEFAULT 'AVAILABLE',
                purchase_price       DECIMAL(12,2),
                purchase_date        DATE,
                insurance_expiry     DATE,
                puc_expiry           DATE,
                fitness_expiry       DATE,
                rc_document_url      TEXT,
                insurance_document_url TEXT,
                next_service_km      DECIMAL(10,2),
                next_service_date    DATE,
                created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                deleted_at           TIMESTAMPTZ
            );
            CREATE INDEX IF NOT EXISTS idx_vehicles_hub    ON vehicles(hub_id)    WHERE deleted_at IS NULL;
            CREATE INDEX IF NOT EXISTS idx_vehicles_status ON vehicles(status)    WHERE deleted_at IS NULL;
            CREATE INDEX IF NOT EXISTS idx_vehicles_reg    ON vehicles(registration_number);

            -- ── GPS Telemetry (partitioned stub) ─────────────────────
            CREATE TABLE IF NOT EXISTS vehicle_gps_telemetry (
                id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                vehicle_id  UUID NOT NULL REFERENCES vehicles(id),
                latitude    DECIMAL(10,8) NOT NULL,
                longitude   DECIMAL(11,8) NOT NULL,
                speed_kmh   DECIMAL(5,2),
                battery_pct DECIMAL(5,2),
                odometer_km DECIMAL(10,2),
                recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_gps_vehicle_time
                ON vehicle_gps_telemetry(vehicle_id, recorded_at DESC);

            -- ── Vehicle Allotments ────────────────────────────────────
            CREATE TABLE IF NOT EXISTS vehicle_allotments (
                id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                rider_id                 UUID NOT NULL,
                vehicle_id               UUID NOT NULL REFERENCES vehicles(id),
                hub_id                   UUID NOT NULL REFERENCES fleet_hubs(id),
                allotted_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                allotted_by_id           UUID NOT NULL,
                expected_return_at       TIMESTAMPTZ,
                returned_at              TIMESTAMPTZ,
                returned_to_hub_id       UUID,
                odometer_at_allotment    DECIMAL(10,2),
                odometer_at_return       DECIMAL(10,2),
                battery_pct_at_allotment DECIMAL(5,2),
                battery_pct_at_return    DECIMAL(5,2),
                condition_at_allotment   TEXT,
                condition_at_return      TEXT,
                damage_notes             TEXT,
                daily_rent_amount        DECIMAL(10,2) NOT NULL,
                security_deposit         DECIMAL(10,2) NOT NULL DEFAULT 0,
                deposit_refunded         BOOLEAN NOT NULL DEFAULT FALSE,
                deposit_refund_amount    DECIMAL(10,2),
                status                   VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
                created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_allotment_active_rider
                ON vehicle_allotments(rider_id) WHERE status = 'ACTIVE';
            CREATE UNIQUE INDEX IF NOT EXISTS idx_allotment_active_vehicle
                ON vehicle_allotments(vehicle_id) WHERE status = 'ACTIVE';
            CREATE INDEX IF NOT EXISTS idx_allotments_rider   ON vehicle_allotments(rider_id);
            CREATE INDEX IF NOT EXISTS idx_allotments_vehicle ON vehicle_allotments(vehicle_id);
            CREATE INDEX IF NOT EXISTS idx_allotments_hub     ON vehicle_allotments(hub_id);
            CREATE INDEX IF NOT EXISTS idx_allotments_status  ON vehicle_allotments(status, allotted_at DESC);

            -- ── Maintenance Alerts ────────────────────────────────────
            CREATE TABLE IF NOT EXISTS maintenance_alerts (
                id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                vehicle_id         UUID NOT NULL REFERENCES vehicles(id),
                alert_type         VARCHAR(100) NOT NULL,
                severity           VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
                message            TEXT NOT NULL,
                is_acknowledged    BOOLEAN NOT NULL DEFAULT FALSE,
                acknowledged_by_id UUID,
                acknowledged_at    TIMESTAMPTZ,
                resolved_at        TIMESTAMPTZ,
                created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_alerts_vehicle
                ON maintenance_alerts(vehicle_id) WHERE is_acknowledged = FALSE;
            CREATE INDEX IF NOT EXISTS idx_alerts_severity
                ON maintenance_alerts(severity, created_at DESC) WHERE is_acknowledged = FALSE;

            -- ── Vehicle Status Audit ──────────────────────────────────
            CREATE TABLE IF NOT EXISTS vehicle_status_audit (
                id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                vehicle_id    UUID NOT NULL REFERENCES vehicles(id),
                old_status    VARCHAR(20),
                new_status    VARCHAR(20) NOT NULL,
                changed_by_id UUID,
                reason        TEXT,
                created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_audit_vehicle_status
                ON vehicle_status_audit(vehicle_id, created_at DESC);

            -- ── updated_at triggers ───────────────────────────────────
            CREATE OR REPLACE FUNCTION set_updated_at()
            RETURNS TRIGGER AS $$
            BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
            $$ LANGUAGE plpgsql;

            DO $$
            DECLARE t TEXT;
            BEGIN
                FOREACH t IN ARRAY ARRAY[
                    'cities','fleet_hubs','vehicles','vehicle_allotments'
                ]
                LOOP
                    EXECUTE format(
                        'DROP TRIGGER IF EXISTS trg_%s_updated_at ON %s;
                         CREATE TRIGGER trg_%s_updated_at
                         BEFORE UPDATE ON %s
                         FOR EACH ROW EXECUTE FUNCTION set_updated_at()',
                        t, t, t, t);
                END LOOP;
            END;
            $$;
            """,
            reverse_sql="""
            DROP TABLE IF EXISTS vehicle_status_audit    CASCADE;
            DROP TABLE IF EXISTS maintenance_alerts      CASCADE;
            DROP TABLE IF EXISTS vehicle_allotments      CASCADE;
            DROP TABLE IF EXISTS vehicle_gps_telemetry   CASCADE;
            DROP TABLE IF EXISTS vehicles                CASCADE;
            DROP TABLE IF EXISTS fleet_hubs              CASCADE;
            DROP TABLE IF EXISTS cities                  CASCADE;
            """
        ),
    ]
