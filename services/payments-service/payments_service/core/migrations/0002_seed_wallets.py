"""Seed wallets for the 10 seeded riders from rider-service."""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [("payments_core", "0001_initial")]

    operations = [
        migrations.RunSQL(
            sql="""
            -- Create wallets for all existing riders (if any)
            INSERT INTO rider_wallets (rider_id, balance, total_earned, total_paid)
            SELECT id,
                   CASE status
                       WHEN 'ACTIVE'    THEN 450.00
                       WHEN 'TRAINING'  THEN 200.00
                       WHEN 'VERIFIED'  THEN 100.00
                       ELSE 0.00
                   END,
                   CASE status WHEN 'ACTIVE' THEN 1200.00 ELSE 0.00 END,
                   CASE status WHEN 'ACTIVE' THEN 750.00  ELSE 0.00 END
            FROM riders
            ON CONFLICT (rider_id) DO NOTHING;

            -- Seed some ledger entries for ACTIVE riders to show history
            INSERT INTO wallet_ledger
                (wallet_id, rider_id, payment_type, amount, direction,
                 balance_after, description, accounting_date)
            SELECT
                w.id,
                w.rider_id,
                'INCENTIVE',
                500.00,
                'C',
                500.00,
                'Welcome bonus on activation',
                CURRENT_DATE - INTERVAL '30 days'
            FROM rider_wallets w
            JOIN riders r ON r.id = w.rider_id
            WHERE r.status = 'ACTIVE'
            LIMIT 5
            ON CONFLICT DO NOTHING;
            """,
            reverse_sql="DELETE FROM rider_wallets;"
        ),
    ]
