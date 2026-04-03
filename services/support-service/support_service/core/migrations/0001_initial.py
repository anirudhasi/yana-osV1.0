from django.db import migrations

class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.RunSQL(
            sql="""
            CREATE SEQUENCE IF NOT EXISTS ticket_seq START 1;

            CREATE TABLE IF NOT EXISTS support_tickets (
                id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                ticket_number      VARCHAR(20) NOT NULL UNIQUE,
                rider_id           UUID NOT NULL,
                category           VARCHAR(30) NOT NULL,
                sub_category       VARCHAR(100),
                subject            VARCHAR(500) NOT NULL,
                description        TEXT NOT NULL,
                attachments        JSONB NOT NULL DEFAULT '[]',
                vehicle_id         UUID,
                allotment_id       UUID,
                demand_slot_id     UUID,
                payment_txn_id     UUID,
                assigned_to_id     UUID,
                assigned_at        TIMESTAMPTZ,
                status             VARCHAR(20) NOT NULL DEFAULT 'OPEN',
                priority           VARCHAR(10) NOT NULL DEFAULT 'MEDIUM',
                resolved_at        TIMESTAMPTZ,
                resolution_notes   TEXT,
                rider_satisfaction INTEGER CHECK (rider_satisfaction BETWEEN 1 AND 5),
                sla_due_at         TIMESTAMPTZ,
                sla_breached       BOOLEAN NOT NULL DEFAULT FALSE,
                whatsapp_thread_id TEXT,
                created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_tickets_rider    ON support_tickets(rider_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_tickets_status   ON support_tickets(status, priority, created_at);
            CREATE INDEX IF NOT EXISTS idx_tickets_assigned ON support_tickets(assigned_to_id) WHERE status NOT IN ('RESOLVED','CLOSED');
            CREATE INDEX IF NOT EXISTS idx_tickets_number   ON support_tickets(ticket_number);

            CREATE TABLE IF NOT EXISTS ticket_messages (
                id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                ticket_id       UUID NOT NULL REFERENCES support_tickets(id),
                sender_type     VARCHAR(10) NOT NULL CHECK (sender_type IN ('RIDER','AGENT','SYSTEM')),
                sender_rider_id UUID,
                sender_admin_id UUID,
                message         TEXT NOT NULL,
                attachments     JSONB NOT NULL DEFAULT '[]',
                is_internal     BOOLEAN NOT NULL DEFAULT FALSE,
                created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_ticket_messages ON ticket_messages(ticket_id, created_at);

            CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$ BEGIN NEW.updated_at = NOW(); RETURN NEW; END; $$ LANGUAGE plpgsql;
            DROP TRIGGER IF EXISTS trg_support_tickets_updated_at ON support_tickets;
            CREATE TRIGGER trg_support_tickets_updated_at BEFORE UPDATE ON support_tickets FOR EACH ROW EXECUTE FUNCTION set_updated_at();
            """,
            reverse_sql="""
            DROP TABLE IF EXISTS ticket_messages  CASCADE;
            DROP TABLE IF EXISTS support_tickets  CASCADE;
            DROP SEQUENCE IF EXISTS ticket_seq;
            """
        ),
    ]
