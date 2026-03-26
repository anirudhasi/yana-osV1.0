from django.db import migrations
from django.contrib.auth.hashers import make_password


class Migration(migrations.Migration):

    dependencies = [("auth_core", "0001_initial")]

    operations = [
        migrations.RunSQL(
            sql=f"""
            INSERT INTO admin_users (id, email, full_name, password_hash, role, is_active)
            VALUES
                (gen_random_uuid(), 'admin@yana.in',  'Super Admin',   '{make_password("Admin@123")}', 'SUPER_ADMIN', TRUE),
                (gen_random_uuid(), 'ops@yana.in',    'Ops Manager',   '{make_password("Ops@123")}',   'HUB_OPS',     TRUE),
                (gen_random_uuid(), 'sales@yana.in',  'Sales Manager', '{make_password("Sales@123")}', 'SALES',       TRUE)
            ON CONFLICT (email) DO NOTHING;
            """,
            reverse_sql="DELETE FROM admin_users WHERE email IN ('admin@yana.in','ops@yana.in','sales@yana.in');"
        ),
    ]
