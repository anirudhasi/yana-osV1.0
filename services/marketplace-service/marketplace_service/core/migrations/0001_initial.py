"""Marketplace service initial migration."""
from django.db import migrations


class Migration(migrations.Migration):
    initial = True
    dependencies = []

    operations = [
        migrations.RunSQL(
            sql="""
            -- ── Clients ───────────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS clients (
                id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name                  VARCHAR(200) NOT NULL,
                category              VARCHAR(100),
                gstin                 VARCHAR(20),
                pan                   VARCHAR(20),
                website               VARCHAR(500),
                primary_contact_name  VARCHAR(200),
                primary_contact_email VARCHAR(255),
                primary_contact_phone VARCHAR(15),
                logo_url              TEXT,
                is_active             BOOLEAN NOT NULL DEFAULT TRUE,
                created_by_id         UUID,
                created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );

            -- ── Client Dark Stores ────────────────────────────────────
            CREATE TABLE IF NOT EXISTS client_dark_stores (
                id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                client_id  UUID NOT NULL REFERENCES clients(id),
                city_id    UUID NOT NULL,
                hub_id     UUID,
                name       VARCHAR(200) NOT NULL,
                address    TEXT NOT NULL,
                latitude   DECIMAL(10,8),
                longitude  DECIMAL(11,8),
                is_active  BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_dark_stores_client ON client_dark_stores(client_id);
            CREATE INDEX IF NOT EXISTS idx_dark_stores_city   ON client_dark_stores(city_id) WHERE is_active = TRUE;

            -- ── Client Contracts ──────────────────────────────────────
            CREATE TABLE IF NOT EXISTS client_contracts (
                id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                client_id         UUID NOT NULL REFERENCES clients(id),
                dark_store_id     UUID REFERENCES client_dark_stores(id),
                contract_start    DATE NOT NULL,
                contract_end      DATE,
                pay_per_order     DECIMAL(8,2),
                pay_per_hour      DECIMAL(8,2),
                pay_per_shift     DECIMAL(8,2),
                minimum_guarantee DECIMAL(10,2),
                sla_terms         JSONB,
                document_url      TEXT,
                is_active         BOOLEAN NOT NULL DEFAULT TRUE,
                created_by_id     UUID,
                created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );

            -- ── Demand Slots ──────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS demand_slots (
                id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                client_id             UUID NOT NULL REFERENCES clients(id),
                dark_store_id         UUID NOT NULL REFERENCES client_dark_stores(id),
                city_id               UUID NOT NULL,
                title                 VARCHAR(200) NOT NULL,
                description           TEXT,
                shift_type            VARCHAR(20)  NOT NULL DEFAULT 'MORNING',
                shift_date            DATE         NOT NULL,
                shift_start_time      TIME         NOT NULL,
                shift_end_time        TIME         NOT NULL,
                shift_duration_hrs    DECIMAL(4,1),
                riders_required       INTEGER      NOT NULL,
                riders_confirmed      INTEGER      NOT NULL DEFAULT 0,
                riders_shown_up       INTEGER      NOT NULL DEFAULT 0,
                pay_structure         VARCHAR(20)  NOT NULL DEFAULT 'PER_SHIFT',
                pay_per_order         DECIMAL(8,2),
                pay_per_shift         DECIMAL(8,2),
                pay_per_hour          DECIMAL(8,2),
                earnings_estimate     DECIMAL(8,2),
                vehicle_required      BOOLEAN      NOT NULL DEFAULT TRUE,
                min_reliability_score DECIMAL(4,2),
                required_hub_ids      JSONB        NOT NULL DEFAULT '[]',
                badge_required        VARCHAR(50),
                city_restriction      BOOLEAN      NOT NULL DEFAULT TRUE,
                status                VARCHAR(20)  NOT NULL DEFAULT 'DRAFT',
                published_by_id       UUID,
                published_at          TIMESTAMPTZ,
                expires_at            TIMESTAMPTZ,
                fill_rate_pct         DECIMAL(5,2) NOT NULL DEFAULT 0,
                created_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
                updated_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_demand_city_date
                ON demand_slots(city_id, shift_date) WHERE status = 'PUBLISHED';
            CREATE INDEX IF NOT EXISTS idx_demand_client   ON demand_slots(client_id);
            CREATE INDEX IF NOT EXISTS idx_demand_status   ON demand_slots(status, shift_date);

            -- ── Demand Applications ───────────────────────────────────
            CREATE TABLE IF NOT EXISTS demand_applications (
                id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                demand_slot_id   UUID        NOT NULL REFERENCES demand_slots(id),
                rider_id         UUID        NOT NULL,
                applied_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                status           VARCHAR(20)  NOT NULL DEFAULT 'APPLIED',
                confirmed_at     TIMESTAMPTZ,
                confirmed_by_id  UUID,
                rejection_reason TEXT,
                no_show_reason   TEXT,
                match_score      DECIMAL(5,2),
                check_in_at      TIMESTAMPTZ,
                check_in_lat     DECIMAL(10,8),
                check_in_lng     DECIMAL(11,8),
                check_out_at     TIMESTAMPTZ,
                check_out_lat    DECIMAL(10,8),
                check_out_lng    DECIMAL(11,8),
                orders_completed INTEGER      NOT NULL DEFAULT 0,
                hours_worked     DECIMAL(5,2),
                earnings_credited DECIMAL(10,2) NOT NULL DEFAULT 0,
                earnings_paid_at TIMESTAMPTZ,
                created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
                updated_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
                UNIQUE (demand_slot_id, rider_id)
            );
            CREATE INDEX IF NOT EXISTS idx_applications_demand
                ON demand_applications(demand_slot_id, status);
            CREATE INDEX IF NOT EXISTS idx_applications_rider
                ON demand_applications(rider_id, applied_at DESC);

            -- ── Demand Slot Audit ─────────────────────────────────────
            CREATE TABLE IF NOT EXISTS demand_slot_audit (
                id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                slot_id         UUID        NOT NULL REFERENCES demand_slots(id),
                action          VARCHAR(50)  NOT NULL,
                old_status      VARCHAR(20),
                new_status      VARCHAR(20),
                performed_by_id UUID,
                metadata        JSONB,
                created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_slot_audit
                ON demand_slot_audit(slot_id, created_at DESC);

            -- ── Triggers ─────────────────────────────────────────────
            CREATE OR REPLACE FUNCTION set_updated_at()
            RETURNS TRIGGER AS $$
            BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
            $$ LANGUAGE plpgsql;

            DO $$
            DECLARE t TEXT;
            BEGIN
                FOREACH t IN ARRAY ARRAY[
                    'clients','client_dark_stores','client_contracts',
                    'demand_slots','demand_applications'
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
            DROP TABLE IF EXISTS demand_slot_audit      CASCADE;
            DROP TABLE IF EXISTS demand_applications    CASCADE;
            DROP TABLE IF EXISTS demand_slots           CASCADE;
            DROP TABLE IF EXISTS client_contracts       CASCADE;
            DROP TABLE IF EXISTS client_dark_stores     CASCADE;
            DROP TABLE IF EXISTS clients                CASCADE;
            """
        ),
    ]
