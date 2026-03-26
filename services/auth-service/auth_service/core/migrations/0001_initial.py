from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE TABLE IF NOT EXISTS admin_users (
                id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                email         VARCHAR(255) NOT NULL UNIQUE,
                phone         VARCHAR(15),
                full_name     VARCHAR(200) NOT NULL,
                password_hash TEXT NOT NULL,
                role          VARCHAR(30) NOT NULL DEFAULT 'VIEWER',
                city_id       UUID,
                hub_id        UUID,
                is_active     BOOLEAN NOT NULL DEFAULT TRUE,
                last_login_at TIMESTAMPTZ,
                created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                deleted_at    TIMESTAMPTZ
            );
            CREATE INDEX IF NOT EXISTS idx_admin_users_email ON admin_users(email) WHERE deleted_at IS NULL;
            CREATE INDEX IF NOT EXISTS idx_admin_users_role  ON admin_users(role)  WHERE deleted_at IS NULL;
            """,
            reverse_sql="DROP TABLE IF EXISTS admin_users;"
        ),
    ]
