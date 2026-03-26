"""
Seed migration: 3 cities, 5 hubs, 10 sample riders across KYC states.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("rider_core", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            -- Cities
            INSERT INTO cities (id, name, state, is_active)
            VALUES
                ('11111111-0000-0000-0000-000000000001', 'Delhi',     'Delhi',       TRUE),
                ('11111111-0000-0000-0000-000000000002', 'Mumbai',    'Maharashtra', TRUE),
                ('11111111-0000-0000-0000-000000000003', 'Bengaluru', 'Karnataka',   TRUE)
            ON CONFLICT DO NOTHING;

            -- Fleet Hubs (require cities table — owned by fleet service, created here for FK)
            CREATE TABLE IF NOT EXISTS fleet_hubs (
                id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                city_id    UUID,
                name       VARCHAR(200) NOT NULL,
                address    TEXT NOT NULL,
                latitude   DECIMAL(10,8),
                longitude  DECIMAL(11,8),
                capacity   INTEGER NOT NULL DEFAULT 0,
                manager_id UUID,
                is_active  BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );

            INSERT INTO fleet_hubs (id, city_id, name, address, capacity, is_active)
            VALUES
                ('22222222-0000-0000-0000-000000000001', '11111111-0000-0000-0000-000000000001', 'Delhi North Hub',  'Rohini, Delhi',          50, TRUE),
                ('22222222-0000-0000-0000-000000000002', '11111111-0000-0000-0000-000000000001', 'Delhi South Hub',  'Okhla, Delhi',           40, TRUE),
                ('22222222-0000-0000-0000-000000000003', '11111111-0000-0000-0000-000000000002', 'Mumbai Central',   'Andheri, Mumbai',        60, TRUE),
                ('22222222-0000-0000-0000-000000000004', '11111111-0000-0000-0000-000000000003', 'Bengaluru North',  'Hebbal, Bengaluru',      45, TRUE),
                ('22222222-0000-0000-0000-000000000005', '11111111-0000-0000-0000-000000000003', 'Bengaluru South',  'Electronic City, BLR',   35, TRUE)
            ON CONFLICT DO NOTHING;

            -- Sample Riders across all KYC states
            INSERT INTO riders (id, full_name, phone, email, status, kyc_status, hub_id, city_id, preferred_language, source, created_at)
            VALUES
                -- Active riders
                (gen_random_uuid(), 'Ramesh Kumar',     '9876500001', 'ramesh@test.in', 'ACTIVE',        'VERIFIED',      '22222222-0000-0000-0000-000000000001', '11111111-0000-0000-0000-000000000001', 'hi', 'app',      NOW() - INTERVAL '30 days'),
                (gen_random_uuid(), 'Suresh Yadav',     '9876500002', NULL,             'ACTIVE',        'VERIFIED',      '22222222-0000-0000-0000-000000000001', '11111111-0000-0000-0000-000000000001', 'hi', 'referral', NOW() - INTERVAL '25 days'),
                (gen_random_uuid(), 'Priya Sharma',     '9876500003', NULL,             'ACTIVE',        'VERIFIED',      '22222222-0000-0000-0000-000000000003', '11111111-0000-0000-0000-000000000002', 'hi', 'app',      NOW() - INTERVAL '20 days'),
                -- In KYC flow
                (gen_random_uuid(), 'Amit Singh',       '9876500004', NULL,             'KYC_PENDING',   'SUBMITTED',     '22222222-0000-0000-0000-000000000004', '11111111-0000-0000-0000-000000000003', 'kn', 'app',      NOW() - INTERVAL '5 days'),
                (gen_random_uuid(), 'Deepak Mehta',     '9876500005', NULL,             'KYC_PENDING',   'UNDER_REVIEW',  '22222222-0000-0000-0000-000000000004', '11111111-0000-0000-0000-000000000003', 'kn', 'app',      NOW() - INTERVAL '3 days'),
                -- New / in docs stage
                (gen_random_uuid(), 'Rahul Gupta',      '9876500006', NULL,             'DOCS_SUBMITTED','PENDING',       '22222222-0000-0000-0000-000000000002', '11111111-0000-0000-0000-000000000001', 'hi', 'whatsapp', NOW() - INTERVAL '2 days'),
                (gen_random_uuid(), 'Monika Patel',     '9876500007', NULL,             'APPLIED',       'PENDING',       NULL,                                  '11111111-0000-0000-0000-000000000002', 'mr', 'app',      NOW() - INTERVAL '1 day'),
                -- KYC failed
                (gen_random_uuid(), 'Vikram Tiwari',    '9876500008', NULL,             'KYC_FAILED',    'REJECTED',      '22222222-0000-0000-0000-000000000005', '11111111-0000-0000-0000-000000000003', 'kn', 'app',      NOW() - INTERVAL '10 days'),
                -- Suspended
                (gen_random_uuid(), 'Arun Nair',        '9876500009', NULL,             'SUSPENDED',     'VERIFIED',      '22222222-0000-0000-0000-000000000005', '11111111-0000-0000-0000-000000000003', 'ta', 'app',      NOW() - INTERVAL '45 days'),
                -- Training
                (gen_random_uuid(), 'Geeta Devi',       '9876500010', NULL,             'TRAINING',      'VERIFIED',      '22222222-0000-0000-0000-000000000003', '11111111-0000-0000-0000-000000000002', 'mr', 'app',      NOW() - INTERVAL '7 days')
            ON CONFLICT (phone) DO NOTHING;
            """,
            reverse_sql="""
            DELETE FROM riders WHERE phone LIKE '98765000%';
            DELETE FROM fleet_hubs WHERE id LIKE '22222222%';
            DELETE FROM cities WHERE id LIKE '11111111%';
            """
        ),
    ]
