"""
Rider service initial migration.
Creates all tables owned by this service.
"""
from django.db import migrations


class Migration(migrations.Migration):

    initial = True
    dependencies = []

    operations = [
        migrations.RunSQL(
            sql="""
            -- ── Riders ────────────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS riders (
                id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                full_name            VARCHAR(200)     NOT NULL,
                phone                VARCHAR(15)      NOT NULL UNIQUE,
                email                VARCHAR(255),
                date_of_birth        DATE,
                gender               VARCHAR(10),
                profile_photo_url    TEXT,
                preferred_language   VARCHAR(20)      NOT NULL DEFAULT 'hi',

                address_line1        TEXT,
                address_line2        TEXT,
                city                 VARCHAR(100),
                state                VARCHAR(100),
                pincode              VARCHAR(10),
                latitude             DECIMAL(10, 8),
                longitude            DECIMAL(11, 8),

                aadhaar_number       VARCHAR(500),
                pan_number           VARCHAR(500),
                dl_number            VARCHAR(500),
                dl_expiry_date       DATE,
                dl_vehicle_class     VARCHAR(50),

                bank_account_number  VARCHAR(500),
                bank_ifsc            VARCHAR(20),
                bank_name            VARCHAR(200),
                upi_id               VARCHAR(200),

                status               VARCHAR(30)      NOT NULL DEFAULT 'APPLIED',
                kyc_status           VARCHAR(30)      NOT NULL DEFAULT 'PENDING',

                aadhaar_verified     BOOLEAN          NOT NULL DEFAULT FALSE,
                pan_verified         BOOLEAN          NOT NULL DEFAULT FALSE,
                dl_verified          BOOLEAN          NOT NULL DEFAULT FALSE,
                bank_verified        BOOLEAN          NOT NULL DEFAULT FALSE,

                hub_id               UUID,
                city_id              UUID,

                training_completed      BOOLEAN       NOT NULL DEFAULT FALSE,
                training_completed_at   TIMESTAMPTZ,
                activated_at            TIMESTAMPTZ,
                activated_by_id         UUID,

                reliability_score    DECIMAL(4, 2),

                referral_code        VARCHAR(20)      UNIQUE,
                referred_by_id       UUID,
                source               VARCHAR(50),

                created_at           TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
                updated_at           TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
                deleted_at           TIMESTAMPTZ
            );

            CREATE INDEX IF NOT EXISTS idx_riders_phone      ON riders(phone) WHERE deleted_at IS NULL;
            CREATE INDEX IF NOT EXISTS idx_riders_status     ON riders(status) WHERE deleted_at IS NULL;
            CREATE INDEX IF NOT EXISTS idx_riders_hub        ON riders(hub_id) WHERE deleted_at IS NULL;
            CREATE INDEX IF NOT EXISTS idx_riders_city       ON riders(city_id) WHERE deleted_at IS NULL;
            CREATE INDEX IF NOT EXISTS idx_riders_name_trgm  ON riders USING GIN (full_name gin_trgm_ops);

            -- ── Rider Nominees ────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS rider_nominees (
                id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                rider_id       UUID        NOT NULL REFERENCES riders(id) ON DELETE CASCADE,
                full_name      VARCHAR(200) NOT NULL,
                relationship   VARCHAR(50)  NOT NULL,
                phone          VARCHAR(15),
                aadhaar_number VARCHAR(500),
                is_primary     BOOLEAN      NOT NULL DEFAULT TRUE,
                created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
                updated_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW()
            );

            CREATE INDEX IF NOT EXISTS idx_nominees_rider ON rider_nominees(rider_id);

            -- ── Rider Documents ───────────────────────────────────────
            CREATE TABLE IF NOT EXISTS rider_documents (
                id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                rider_id         UUID        NOT NULL REFERENCES riders(id) ON DELETE CASCADE,
                document_type    VARCHAR(50)  NOT NULL,
                file_url         TEXT         NOT NULL,
                file_name        VARCHAR(500),
                file_size_bytes  INTEGER,
                mime_type        VARCHAR(100),
                status           VARCHAR(30)  NOT NULL DEFAULT 'PENDING',
                verified_by_id   UUID,
                verified_at      TIMESTAMPTZ,
                rejection_reason TEXT,
                external_ref_id  TEXT,
                created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
                updated_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
            );

            CREATE INDEX IF NOT EXISTS idx_documents_rider
                ON rider_documents(rider_id);
            CREATE INDEX IF NOT EXISTS idx_documents_type_status
                ON rider_documents(document_type, status);

            -- ── KYC Verification Logs ─────────────────────────────────
            CREATE TABLE IF NOT EXISTS kyc_verification_logs (
                id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                rider_id          UUID        NOT NULL REFERENCES riders(id),
                document_id       UUID        REFERENCES rider_documents(id),
                action            VARCHAR(50)  NOT NULL,
                performed_by_id   UUID,
                provider          VARCHAR(50),
                provider_ref_id   TEXT,
                provider_response JSONB,
                old_status        VARCHAR(30),
                new_status        VARCHAR(30)  NOT NULL,
                notes             TEXT,
                created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW()
            );

            CREATE INDEX IF NOT EXISTS idx_kyc_logs_rider
                ON kyc_verification_logs(rider_id, created_at DESC);

            -- ── Rider Status Audit ────────────────────────────────────
            CREATE TABLE IF NOT EXISTS rider_status_audit (
                id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                rider_id      UUID        NOT NULL REFERENCES riders(id),
                old_status    VARCHAR(30),
                new_status    VARCHAR(30)  NOT NULL,
                changed_by_id UUID,
                reason        TEXT,
                metadata      JSONB,
                created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
            );

            CREATE INDEX IF NOT EXISTS idx_audit_rider_status
                ON rider_status_audit(rider_id, created_at DESC);

            -- ── Trigger: auto-update updated_at ──────────────────────
            CREATE OR REPLACE FUNCTION set_updated_at()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = NOW();
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;

            DO $$
            DECLARE t TEXT;
            BEGIN
                FOREACH t IN ARRAY ARRAY['riders','rider_nominees','rider_documents']
                LOOP
                    EXECUTE format(
                        'DROP TRIGGER IF EXISTS trg_%s_updated_at ON %s;
                         CREATE TRIGGER trg_%s_updated_at
                         BEFORE UPDATE ON %s
                         FOR EACH ROW EXECUTE FUNCTION set_updated_at()',
                        t, t, t, t
                    );
                END LOOP;
            END;
            $$;
            """,
            reverse_sql="""
            DROP TABLE IF EXISTS rider_status_audit    CASCADE;
            DROP TABLE IF EXISTS kyc_verification_logs CASCADE;
            DROP TABLE IF EXISTS rider_documents       CASCADE;
            DROP TABLE IF EXISTS rider_nominees        CASCADE;
            DROP TABLE IF EXISTS riders                CASCADE;
            """
        ),
    ]
