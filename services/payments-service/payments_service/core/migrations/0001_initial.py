"""Payments service initial migration — creates all owned tables."""
from django.db import migrations


class Migration(migrations.Migration):

    initial = True
    dependencies = []

    operations = [
        migrations.RunSQL(
            sql="""
            -- ── Rider Wallets ─────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS rider_wallets (
                id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                rider_id              UUID NOT NULL UNIQUE,
                balance               DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                total_earned          DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                total_paid            DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                total_pending_dues    DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                security_deposit_held DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                version               INTEGER        NOT NULL DEFAULT 0,
                created_at            TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
                updated_at            TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
                CONSTRAINT wallet_balance_floor CHECK (balance >= -500.00)
            );
            CREATE INDEX IF NOT EXISTS idx_wallets_rider ON rider_wallets(rider_id);

            -- ── Wallet Ledger (append-only) ───────────────────────────
            CREATE TABLE IF NOT EXISTS wallet_ledger (
                id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                wallet_id       UUID        NOT NULL REFERENCES rider_wallets(id),
                rider_id        UUID        NOT NULL,
                payment_type    VARCHAR(30)  NOT NULL,
                amount          DECIMAL(12,2) NOT NULL,
                direction       CHAR(1)      NOT NULL CHECK (direction IN ('C','D')),
                balance_after   DECIMAL(12,2) NOT NULL,
                reference_id    UUID,
                reference_type  VARCHAR(50),
                description     TEXT,
                payment_gateway VARCHAR(50),
                gateway_txn_id  TEXT,
                upi_ref_id      TEXT,
                accounting_date DATE         NOT NULL DEFAULT CURRENT_DATE,
                created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_ledger_wallet
                ON wallet_ledger(wallet_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_ledger_rider
                ON wallet_ledger(rider_id, accounting_date DESC);
            CREATE INDEX IF NOT EXISTS idx_ledger_type
                ON wallet_ledger(payment_type, accounting_date);
            CREATE INDEX IF NOT EXISTS idx_ledger_gateway_txn
                ON wallet_ledger(gateway_txn_id) WHERE gateway_txn_id IS NOT NULL;

            -- ── Payment Transactions ──────────────────────────────────
            CREATE TABLE IF NOT EXISTS payment_transactions (
                id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                rider_id             UUID        NOT NULL,
                ledger_entry_id      UUID        REFERENCES wallet_ledger(id),
                amount               DECIMAL(12,2) NOT NULL,
                currency             CHAR(3)      NOT NULL DEFAULT 'INR',
                gateway              VARCHAR(50)  NOT NULL,
                gateway_order_id     TEXT         UNIQUE,
                gateway_payment_id   TEXT,
                gateway_signature    TEXT,
                gateway_status       VARCHAR(50),
                gateway_raw_response JSONB,
                status               VARCHAR(20)  NOT NULL DEFAULT 'PENDING',
                failure_reason       TEXT,
                payment_type         VARCHAR(30),
                initiated_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
                completed_at         TIMESTAMPTZ,
                created_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
                updated_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_txn_rider
                ON payment_transactions(rider_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_txn_status
                ON payment_transactions(status, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_txn_gateway_order
                ON payment_transactions(gateway_order_id) WHERE gateway_order_id IS NOT NULL;

            -- ── Rent Schedule ─────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS rent_schedule (
                id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                allotment_id       UUID        NOT NULL,
                rider_id           UUID        NOT NULL,
                due_date           DATE        NOT NULL,
                amount             DECIMAL(10,2) NOT NULL,
                status             VARCHAR(20)  NOT NULL DEFAULT 'PENDING',
                paid_ledger_id     UUID        REFERENCES wallet_ledger(id),
                paid_at            TIMESTAMPTZ,
                overdue_penalty    DECIMAL(10,2) NOT NULL DEFAULT 0.00,
                penalty_applied_at TIMESTAMPTZ,
                days_overdue       INTEGER      NOT NULL DEFAULT 0,
                created_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
                updated_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_rent_allotment ON rent_schedule(allotment_id);
            CREATE INDEX IF NOT EXISTS idx_rent_rider     ON rent_schedule(rider_id, due_date);
            CREATE INDEX IF NOT EXISTS idx_rent_due       ON rent_schedule(due_date, status);

            -- ── UPI Mandates ──────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS upi_mandates (
                id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                rider_id              UUID        NOT NULL UNIQUE,
                upi_id                VARCHAR(200) NOT NULL,
                razorpay_mandate_id   TEXT        UNIQUE,
                razorpay_customer_id  TEXT,
                max_amount            DECIMAL(10,2) NOT NULL DEFAULT 500.00,
                is_active             BOOLEAN      NOT NULL DEFAULT FALSE,
                activated_at          TIMESTAMPTZ,
                revoked_at            TIMESTAMPTZ,
                created_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
                updated_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_upi_mandates_rider ON upi_mandates(rider_id);

            -- ── updated_at triggers ───────────────────────────────────
            CREATE OR REPLACE FUNCTION set_updated_at()
            RETURNS TRIGGER AS $$
            BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
            $$ LANGUAGE plpgsql;

            DO $$
            DECLARE t TEXT;
            BEGIN
                FOREACH t IN ARRAY ARRAY[
                    'rider_wallets','payment_transactions','rent_schedule','upi_mandates'
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

            -- ── Wallet optimistic lock guard ──────────────────────────
            CREATE OR REPLACE FUNCTION check_wallet_version()
            RETURNS TRIGGER AS $$
            BEGIN
                IF NEW.version != OLD.version + 1 THEN
                    RAISE EXCEPTION
                        'Wallet optimistic lock conflict: expected version %, got %',
                        OLD.version + 1, NEW.version;
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;

            DROP TRIGGER IF EXISTS trg_wallet_version ON rider_wallets;
            CREATE TRIGGER trg_wallet_version
            BEFORE UPDATE OF version ON rider_wallets
            FOR EACH ROW EXECUTE FUNCTION check_wallet_version();
            """,
            reverse_sql="""
            DROP TABLE IF EXISTS upi_mandates          CASCADE;
            DROP TABLE IF EXISTS rent_schedule         CASCADE;
            DROP TABLE IF EXISTS payment_transactions  CASCADE;
            DROP TABLE IF EXISTS wallet_ledger         CASCADE;
            DROP TABLE IF EXISTS rider_wallets         CASCADE;
            """
        ),
    ]
