from django.db import migrations

class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.RunSQL(
            sql="""
            CREATE TABLE IF NOT EXISTS maintenance_logs (
                id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                vehicle_id           UUID NOT NULL,
                hub_id               UUID NOT NULL,
                maintenance_type     VARCHAR(30) NOT NULL,
                status               VARCHAR(20) NOT NULL DEFAULT 'SCHEDULED',
                scheduled_date       DATE,
                started_at           TIMESTAMPTZ,
                completed_at         TIMESTAMPTZ,
                downtime_hours       DECIMAL(6,2),
                description          TEXT,
                parts_replaced       JSONB,
                labour_cost          DECIMAL(10,2) NOT NULL DEFAULT 0,
                parts_cost           DECIMAL(10,2) NOT NULL DEFAULT 0,
                odometer_at_service  DECIMAL(10,2),
                next_service_km      DECIMAL(10,2),
                next_service_date    DATE,
                performed_by_vendor  VARCHAR(200),
                invoice_url          TEXT,
                logged_by_id         UUID NOT NULL,
                notes                TEXT,
                created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_maint_vehicle ON maintenance_logs(vehicle_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_maint_hub     ON maintenance_logs(hub_id);
            CREATE INDEX IF NOT EXISTS idx_maint_status  ON maintenance_logs(status, scheduled_date);

            CREATE TABLE IF NOT EXISTS maintenance_alerts (
                id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                vehicle_id         UUID NOT NULL,
                alert_type         VARCHAR(100) NOT NULL,
                severity           VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
                message            TEXT NOT NULL,
                is_acknowledged    BOOLEAN NOT NULL DEFAULT FALSE,
                acknowledged_by_id UUID,
                acknowledged_at    TIMESTAMPTZ,
                resolved_at        TIMESTAMPTZ,
                created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_alerts_vehicle  ON maintenance_alerts(vehicle_id, is_acknowledged);
            CREATE INDEX IF NOT EXISTS idx_alerts_severity ON maintenance_alerts(severity, created_at DESC) WHERE is_acknowledged=FALSE;

            CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$ BEGIN NEW.updated_at = NOW(); RETURN NEW; END; $$ LANGUAGE plpgsql;
            DROP TRIGGER IF EXISTS trg_maintenance_logs_updated_at ON maintenance_logs;
            CREATE TRIGGER trg_maintenance_logs_updated_at BEFORE UPDATE ON maintenance_logs FOR EACH ROW EXECUTE FUNCTION set_updated_at();
            """,
            reverse_sql="DROP TABLE IF EXISTS maintenance_alerts CASCADE; DROP TABLE IF EXISTS maintenance_logs CASCADE;"
        ),
    ]
