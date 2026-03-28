"""Seed: 3 clients (Blinkit, BigBasket, JioMart), dark stores, sample demand slots."""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [("marketplace_core", "0001_initial")]

    operations = [
        migrations.RunSQL(
            sql="""
            -- ── Clients ──────────────────────────────────────────
            INSERT INTO clients (id, name, category, primary_contact_name,
                                 primary_contact_email, primary_contact_phone, is_active)
            VALUES
                ('aaaaaaaa-0000-0000-0000-000000000001', 'Blinkit',    'quick_commerce', 'Blinkit Ops',    'ops@blinkit.com',    '9800000001', TRUE),
                ('aaaaaaaa-0000-0000-0000-000000000002', 'BigBasket',  'grocery',        'BB Ops',          'ops@bigbasket.com',  '9800000002', TRUE),
                ('aaaaaaaa-0000-0000-0000-000000000003', 'JioMart',    'grocery',        'JioMart Ops',     'ops@jiomart.com',    '9800000003', TRUE)
            ON CONFLICT DO NOTHING;

            -- ── Dark Stores (Delhi + Mumbai + Bengaluru) ──────────
            INSERT INTO client_dark_stores (id, client_id, city_id, hub_id, name, address, latitude, longitude, is_active)
            VALUES
                -- Blinkit
                ('bbbbbbbb-0000-0000-0000-000000000001','aaaaaaaa-0000-0000-0000-000000000001','11111111-0000-0000-0000-000000000001','22222222-0000-0000-0000-000000000001','Blinkit Rohini',         'Sector 14, Rohini, Delhi',       28.7234,77.0987,TRUE),
                ('bbbbbbbb-0000-0000-0000-000000000002','aaaaaaaa-0000-0000-0000-000000000001','11111111-0000-0000-0000-000000000001','22222222-0000-0000-0000-000000000002','Blinkit Okhla',          'Phase III, Okhla, Delhi',        28.5243,77.2687,TRUE),
                ('bbbbbbbb-0000-0000-0000-000000000003','aaaaaaaa-0000-0000-0000-000000000001','11111111-0000-0000-0000-000000000002','22222222-0000-0000-0000-000000000003','Blinkit Andheri',        'Andheri East, Mumbai',           19.1182,72.8685,TRUE),
                ('bbbbbbbb-0000-0000-0000-000000000004','aaaaaaaa-0000-0000-0000-000000000001','11111111-0000-0000-0000-000000000003','22222222-0000-0000-0000-000000000004','Blinkit Hebbal',         'Hebbal, Bengaluru',              13.0450,77.5970,TRUE),
                -- BigBasket
                ('bbbbbbbb-0000-0000-0000-000000000005','aaaaaaaa-0000-0000-0000-000000000002','11111111-0000-0000-0000-000000000001','22222222-0000-0000-0000-000000000001','BB Delhi North',         'Pitampura, Delhi',               28.7015,77.1300,TRUE),
                ('bbbbbbbb-0000-0000-0000-000000000006','aaaaaaaa-0000-0000-0000-000000000002','11111111-0000-0000-0000-000000000003','22222222-0000-0000-0000-000000000005','BB Electronic City',     'Electronic City, Bengaluru',     12.8392,77.6760,TRUE),
                -- JioMart
                ('bbbbbbbb-0000-0000-0000-000000000007','aaaaaaaa-0000-0000-0000-000000000003','11111111-0000-0000-0000-000000000001','22222222-0000-0000-0000-000000000002','JioMart South Delhi',    'Saket, Delhi',                   28.5245,77.2190,TRUE),
                ('bbbbbbbb-0000-0000-0000-000000000008','aaaaaaaa-0000-0000-0000-000000000003','11111111-0000-0000-0000-000000000002','22222222-0000-0000-0000-000000000003','JioMart Goregaon',       'Goregaon West, Mumbai',          19.1663,72.8526,TRUE)
            ON CONFLICT DO NOTHING;

            -- ── Contracts ─────────────────────────────────────────
            INSERT INTO client_contracts (client_id, dark_store_id, contract_start, pay_per_order, pay_per_shift, is_active)
            VALUES
                ('aaaaaaaa-0000-0000-0000-000000000001','bbbbbbbb-0000-0000-0000-000000000001','2025-01-01',35.00,NULL,TRUE),
                ('aaaaaaaa-0000-0000-0000-000000000001','bbbbbbbb-0000-0000-0000-000000000002','2025-01-01',35.00,NULL,TRUE),
                ('aaaaaaaa-0000-0000-0000-000000000002','bbbbbbbb-0000-0000-0000-000000000005','2025-01-01',NULL,600.00,TRUE),
                ('aaaaaaaa-0000-0000-0000-000000000003','bbbbbbbb-0000-0000-0000-000000000007','2025-01-01',NULL,550.00,TRUE)
            ON CONFLICT DO NOTHING;

            -- ── Sample Demand Slots (today + next 7 days) ─────────
            INSERT INTO demand_slots (
                client_id, dark_store_id, city_id,
                title, shift_type,
                shift_date, shift_start_time, shift_end_time, shift_duration_hrs,
                riders_required, pay_structure, pay_per_order, earnings_estimate,
                vehicle_required, status, published_at
            )
            VALUES
                -- Blinkit Rohini — Morning today
                ('aaaaaaaa-0000-0000-0000-000000000001','bbbbbbbb-0000-0000-0000-000000000001','11111111-0000-0000-0000-000000000001',
                 'Blinkit Rohini — Morning Shift','MORNING',
                 CURRENT_DATE,'06:00','14:00',8.0,
                 5,'PER_ORDER',35.00,700.00,
                 TRUE,'PUBLISHED',NOW()),

                -- Blinkit Okhla — Afternoon today
                ('aaaaaaaa-0000-0000-0000-000000000001','bbbbbbbb-0000-0000-0000-000000000002','11111111-0000-0000-0000-000000000001',
                 'Blinkit Okhla — Afternoon Shift','AFTERNOON',
                 CURRENT_DATE,'14:00','22:00',8.0,
                 4,'PER_ORDER',35.00,700.00,
                 TRUE,'PUBLISHED',NOW()),

                -- Blinkit Andheri — Morning today
                ('aaaaaaaa-0000-0000-0000-000000000001','bbbbbbbb-0000-0000-0000-000000000003','11111111-0000-0000-0000-000000000002',
                 'Blinkit Andheri — Morning Shift','MORNING',
                 CURRENT_DATE,'06:00','14:00',8.0,
                 6,'PER_ORDER',38.00,760.00,
                 TRUE,'PUBLISHED',NOW()),

                -- BigBasket Delhi — today
                ('aaaaaaaa-0000-0000-0000-000000000002','bbbbbbbb-0000-0000-0000-000000000005','11111111-0000-0000-0000-000000000001',
                 'BigBasket Delhi North — Full Day','MORNING',
                 CURRENT_DATE,'08:00','20:00',12.0,
                 3,'PER_SHIFT',NULL,600.00,
                 TRUE,'PUBLISHED',NOW()),

                -- JioMart South Delhi — tomorrow
                ('aaaaaaaa-0000-0000-0000-000000000003','bbbbbbbb-0000-0000-0000-000000000007','11111111-0000-0000-0000-000000000001',
                 'JioMart South Delhi — Morning','MORNING',
                 CURRENT_DATE + 1,'06:00','14:00',8.0,
                 4,'PER_SHIFT',NULL,550.00,
                 TRUE,'PUBLISHED',NOW()),

                -- Blinkit Hebbal BLR — tomorrow
                ('aaaaaaaa-0000-0000-0000-000000000001','bbbbbbbb-0000-0000-0000-000000000004','11111111-0000-0000-0000-000000000003',
                 'Blinkit Hebbal — Morning Shift','MORNING',
                 CURRENT_DATE + 1,'06:00','14:00',8.0,
                 5,'PER_ORDER',40.00,800.00,
                 TRUE,'DRAFT',NULL),

                -- BigBasket Electronic City — draft for next week
                ('aaaaaaaa-0000-0000-0000-000000000002','bbbbbbbb-0000-0000-0000-000000000006','11111111-0000-0000-0000-000000000003',
                 'BB Electronic City — Weekend Special','MORNING',
                 CURRENT_DATE + 5,'07:00','19:00',12.0,
                 8,'HYBRID',20.00,800.00,
                 TRUE,'DRAFT',NULL)
            ON CONFLICT DO NOTHING;
            """,
            reverse_sql="""
            DELETE FROM demand_applications WHERE demand_slot_id IN (SELECT id FROM demand_slots WHERE client_id IN (SELECT id FROM clients WHERE name IN ('Blinkit','BigBasket','JioMart')));
            DELETE FROM demand_slots        WHERE client_id IN (SELECT id FROM clients WHERE name IN ('Blinkit','BigBasket','JioMart'));
            DELETE FROM client_contracts    WHERE client_id IN (SELECT id FROM clients WHERE name IN ('Blinkit','BigBasket','JioMart'));
            DELETE FROM client_dark_stores  WHERE client_id IN (SELECT id FROM clients WHERE name IN ('Blinkit','BigBasket','JioMart'));
            DELETE FROM clients             WHERE name IN ('Blinkit','BigBasket','JioMart');
            """
        ),
    ]
