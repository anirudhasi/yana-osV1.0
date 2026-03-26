"""Seed: 3 cities, 5 hubs, 20 EV vehicles across statuses."""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [("fleet_core", "0001_initial")]

    operations = [
        migrations.RunSQL(
            sql="""
            -- Cities
            INSERT INTO cities (id, name, state, is_active) VALUES
                ('11111111-0000-0000-0000-000000000001','Delhi',    'Delhi',       TRUE),
                ('11111111-0000-0000-0000-000000000002','Mumbai',   'Maharashtra', TRUE),
                ('11111111-0000-0000-0000-000000000003','Bengaluru','Karnataka',   TRUE)
            ON CONFLICT DO NOTHING;

            -- Hubs
            INSERT INTO fleet_hubs (id, city_id, name, address, latitude, longitude, capacity, is_active) VALUES
                ('22222222-0000-0000-0000-000000000001','11111111-0000-0000-0000-000000000001','Delhi North Hub', 'Rohini Sector 14, Delhi',       28.7041,77.1025,50,TRUE),
                ('22222222-0000-0000-0000-000000000002','11111111-0000-0000-0000-000000000001','Delhi South Hub', 'Okhla Industrial Area, Delhi',  28.5355,77.2507,40,TRUE),
                ('22222222-0000-0000-0000-000000000003','11111111-0000-0000-0000-000000000002','Mumbai Central',  'Andheri East, Mumbai',          19.1136,72.8697,60,TRUE),
                ('22222222-0000-0000-0000-000000000004','11111111-0000-0000-0000-000000000003','BLR North Hub',   'Hebbal, Bengaluru',             13.0435,77.5971,45,TRUE),
                ('22222222-0000-0000-0000-000000000005','11111111-0000-0000-0000-000000000003','BLR South Hub',   'Electronic City, Bengaluru',    12.8393,77.6770,35,TRUE)
            ON CONFLICT DO NOTHING;

            -- 20 EV Vehicles (spread across hubs and statuses)
            INSERT INTO vehicles (
                id, hub_id, registration_number, make, model,
                manufacturing_year, color,
                battery_capacity_kwh, battery_health_pct, range_km,
                current_odometer_km, battery_level_pct,
                status, purchase_price, purchase_date,
                insurance_expiry, puc_expiry, next_service_km, next_service_date
            ) VALUES
                (gen_random_uuid(),'22222222-0000-0000-0000-000000000001','DL01AB0001','Ather','450X',2023,'Grey',   2.90,94,85,  1230,78,'AVAILABLE',145000,'2023-01-15','2025-01-15','2025-06-01',5000,'2025-06-01'),
                (gen_random_uuid(),'22222222-0000-0000-0000-000000000001','DL01AB0002','Ola',  'S1 Pro',2023,'White', 3.97,89,135, 3410,55,'ALLOCATED', 130000,'2023-02-10','2025-02-10','2025-07-01',8000,'2025-07-01'),
                (gen_random_uuid(),'22222222-0000-0000-0000-000000000001','DL01AB0003','Ather','450X',2022,'Black',  2.90,76,73,  8920,42,'AVAILABLE',145000,'2022-08-01','2024-08-01','2025-08-01',9500,'2025-04-15'),
                (gen_random_uuid(),'22222222-0000-0000-0000-000000000001','DL01AB0004','Hero', 'Optima',2023,'Blue',  1.21,91,82,  2100,88,'MAINTENANCE',89000,'2023-03-20','2025-03-20','2025-09-01',6000,'2025-09-01'),
                (gen_random_uuid(),'22222222-0000-0000-0000-000000000002','DL02CD0001','Ola',  'S1',2023,'Red',      2.98,85,101, 4560,63,'AVAILABLE',115000,'2023-04-10','2025-04-10','2025-05-01',7000,'2025-05-01'),
                (gen_random_uuid(),'22222222-0000-0000-0000-000000000002','DL02CD0002','Bajaj','Chetak',2023,'Blue',  3.00,92,95,  1890,91,'ALLOCATED', 135000,'2023-05-15','2025-05-15','2025-10-01',5500,'2025-10-01'),
                (gen_random_uuid(),'22222222-0000-0000-0000-000000000002','DL02CD0003','Ather','450S',2023,'White',  2.40,88,80,  3200,74,'AVAILABLE',125000,'2023-06-01','2025-06-01','2025-11-01',7500,'2025-11-01'),
                (gen_random_uuid(),'22222222-0000-0000-0000-000000000002','DL02CD0004','Hero', 'Optima',2022,'Grey',  1.21,68,56,  9400,31,'MAINTENANCE',89000,'2022-10-10','2024-10-10','2025-04-01',9800,'2025-04-01'),
                (gen_random_uuid(),'22222222-0000-0000-0000-000000000003','MH02EF0001','Ola',  'S1 Pro',2023,'Black', 3.97,95,140, 1100,85,'AVAILABLE',130000,'2023-07-01','2025-07-01','2025-12-01',4000,'2025-12-01'),
                (gen_random_uuid(),'22222222-0000-0000-0000-000000000003','MH02EF0002','Ather','450X',2023,'Red',    2.90,90,87,  2400,67,'ALLOCATED', 145000,'2023-08-15','2025-08-15','2026-01-01',6500,'2026-01-01'),
                (gen_random_uuid(),'22222222-0000-0000-0000-000000000003','MH02EF0003','Bajaj','Chetak',2022,'White', 3.00,79,80,  7800,52,'AVAILABLE',135000,'2022-11-01','2024-11-01','2025-05-15',9200,'2025-05-15'),
                (gen_random_uuid(),'22222222-0000-0000-0000-000000000003','MH02EF0004','Ola',  'S1',2023,'Blue',     2.98,87,100, 3600,76,'AVAILABLE',115000,'2023-09-01','2025-09-01','2026-02-01',7000,'2026-02-01'),
                (gen_random_uuid(),'22222222-0000-0000-0000-000000000003','MH02EF0005','Hero', 'Optima',2023,'Grey',  1.21,93,84,  1500,89,'ALLOCATED', 89000,'2023-10-01','2025-10-01','2026-03-01',5000,'2026-03-01'),
                (gen_random_uuid(),'22222222-0000-0000-0000-000000000004','KA01GH0001','Ather','450X',2023,'Black',  2.90,96,88,   900,94,'AVAILABLE',145000,'2023-11-01','2025-11-01','2026-04-01',3500,'2026-04-01'),
                (gen_random_uuid(),'22222222-0000-0000-0000-000000000004','KA01GH0002','Ola',  'S1 Pro',2023,'White', 3.97,91,138, 2800,71,'ALLOCATED', 130000,'2023-12-01','2025-12-01','2026-05-01',6000,'2026-05-01'),
                (gen_random_uuid(),'22222222-0000-0000-0000-000000000004','KA01GH0003','Bajaj','Chetak',2022,'Blue',  3.00,72,72,  8100,44,'MAINTENANCE',135000,'2022-12-15','2024-12-15','2025-06-15',9500,'2025-06-15'),
                (gen_random_uuid(),'22222222-0000-0000-0000-000000000004','KA01GH0004','Hero', 'Optima',2023,'Red',   1.21,88,81,  3300,77,'AVAILABLE',89000,'2024-01-10','2026-01-10','2026-06-01',7000,'2026-06-01'),
                (gen_random_uuid(),'22222222-0000-0000-0000-000000000005','KA05IJ0001','Ather','450S',2023,'Grey',   2.40,94,82,  1700,83,'AVAILABLE',125000,'2024-02-01','2026-02-01','2026-07-01',5500,'2026-07-01'),
                (gen_random_uuid(),'22222222-0000-0000-0000-000000000005','KA05IJ0002','Ola',  'S1',2023,'Black',    2.98,89,102, 2200,68,'ALLOCATED', 115000,'2024-03-01','2026-03-01','2026-08-01',6000,'2026-08-01'),
                (gen_random_uuid(),'22222222-0000-0000-0000-000000000005','KA05IJ0003','Ather','450X',2023,'White',  2.90,97,89,   600,96,'AVAILABLE',145000,'2024-04-01','2026-04-01','2026-09-01',3000,'2026-09-01')
            ON CONFLICT (registration_number) DO NOTHING;
            """,
            reverse_sql="""
            DELETE FROM vehicles WHERE registration_number LIKE 'DL01AB%' OR registration_number LIKE 'DL02CD%' OR registration_number LIKE 'MH02EF%' OR registration_number LIKE 'KA01GH%' OR registration_number LIKE 'KA05IJ%';
            DELETE FROM fleet_hubs WHERE id LIKE '22222222%';
            DELETE FROM cities WHERE id LIKE '11111111%';
            """
        ),
    ]
