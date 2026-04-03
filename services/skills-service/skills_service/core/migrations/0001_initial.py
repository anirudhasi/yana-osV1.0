from django.db import migrations

class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.RunSQL(
            sql="""
            CREATE TABLE IF NOT EXISTS skill_modules (
                id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                title          VARCHAR(300) NOT NULL,
                title_hi       VARCHAR(300),
                description    TEXT,
                description_hi TEXT,
                thumbnail_url  TEXT,
                sequence_order INTEGER NOT NULL DEFAULT 0,
                is_mandatory   BOOLEAN NOT NULL DEFAULT FALSE,
                is_published   BOOLEAN NOT NULL DEFAULT FALSE,
                created_by_id  UUID,
                created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS skill_videos (
                id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                module_id      UUID NOT NULL REFERENCES skill_modules(id),
                title          VARCHAR(300) NOT NULL,
                title_hi       VARCHAR(300),
                video_url      TEXT NOT NULL,
                thumbnail_url  TEXT,
                duration_secs  INTEGER,
                sequence_order INTEGER NOT NULL DEFAULT 0,
                points_reward  INTEGER NOT NULL DEFAULT 10,
                has_quiz       BOOLEAN NOT NULL DEFAULT FALSE,
                quiz_questions JSONB,
                quiz_pass_score INTEGER NOT NULL DEFAULT 70,
                is_published   BOOLEAN NOT NULL DEFAULT FALSE,
                created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_videos_module ON skill_videos(module_id, sequence_order);

            CREATE TABLE IF NOT EXISTS rider_skill_progress (
                id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                rider_id        UUID NOT NULL,
                module_id       UUID NOT NULL REFERENCES skill_modules(id),
                video_id        UUID NOT NULL REFERENCES skill_videos(id),
                started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                completed_at    TIMESTAMPTZ,
                watch_time_secs INTEGER NOT NULL DEFAULT 0,
                is_completed    BOOLEAN NOT NULL DEFAULT FALSE,
                quiz_score      INTEGER,
                quiz_passed     BOOLEAN,
                points_earned   INTEGER NOT NULL DEFAULT 0,
                UNIQUE (rider_id, video_id)
            );
            CREATE INDEX IF NOT EXISTS idx_skill_progress_rider ON rider_skill_progress(rider_id);

            CREATE TABLE IF NOT EXISTS rider_gamification (
                id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                rider_id         UUID NOT NULL UNIQUE,
                total_points     INTEGER NOT NULL DEFAULT 0,
                current_level    INTEGER NOT NULL DEFAULT 1,
                streak_days      INTEGER NOT NULL DEFAULT 0,
                longest_streak   INTEGER NOT NULL DEFAULT 0,
                last_activity_at TIMESTAMPTZ,
                updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS rider_badges (
                id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                rider_id      UUID NOT NULL,
                badge_code    VARCHAR(50) NOT NULL,
                badge_name    VARCHAR(100) NOT NULL,
                badge_name_hi VARCHAR(100),
                badge_icon_url TEXT,
                earned_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE (rider_id, badge_code)
            );
            CREATE INDEX IF NOT EXISTS idx_badges_rider ON rider_badges(rider_id);

            -- Seed mandatory training modules
            INSERT INTO skill_modules (id, title, title_hi, description, sequence_order, is_mandatory, is_published) VALUES
                ('cccccccc-0000-0000-0000-000000000001','App Usage & Navigation',      'ऐप का उपयोग और नेविगेशन',   'Learn how to use the Yana rider app effectively.',         1, TRUE,  TRUE),
                ('cccccccc-0000-0000-0000-000000000002','Delivery Etiquette',          'डिलीवरी शिष्टाचार',         'Professional conduct with customers and at dark stores.',  2, TRUE,  TRUE),
                ('cccccccc-0000-0000-0000-000000000003','Road Safety & Traffic Rules', 'सड़क सुरक्षा और यातायात नियम','Essential safety rules for two-wheeler delivery riders.', 3, TRUE,  TRUE),
                ('cccccccc-0000-0000-0000-000000000004','EV Vehicle Care',             'ईवी वाहन देखभाल',           'Proper care and charging of electric scooters.',           4, TRUE,  TRUE),
                ('cccccccc-0000-0000-0000-000000000005','Earnings & Wallet',           'कमाई और वॉलेट',             'Understanding your wallet, rent, and incentives.',         5, FALSE, TRUE),
                ('cccccccc-0000-0000-0000-000000000006','Advanced Riding Skills',      'उन्नत राइडिंग कौशल',        'Skill upgrades for experienced riders.',                   6, FALSE, TRUE)
            ON CONFLICT DO NOTHING;

            -- Seed sample videos
            INSERT INTO skill_videos (module_id, title, title_hi, video_url, duration_secs, sequence_order, points_reward, has_quiz, quiz_questions, is_published) VALUES
                ('cccccccc-0000-0000-0000-000000000001','Getting Started with Yana App','याना ऐप से शुरुआत','https://yana-skills.s3.ap-south-1.amazonaws.com/videos/app-intro.mp4',300,1,10,FALSE,NULL,TRUE),
                ('cccccccc-0000-0000-0000-000000000001','Booking Your First Vehicle',  'पहला वाहन बुक करें',    'https://yana-skills.s3.ap-south-1.amazonaws.com/videos/vehicle-booking.mp4',240,2,10,FALSE,NULL,TRUE),
                ('cccccccc-0000-0000-0000-000000000002','Greeting Customers Professionally','ग्राहकों से व्यावसायिक व्यवहार','https://yana-skills.s3.ap-south-1.amazonaws.com/videos/customer-etiquette.mp4',420,1,15,TRUE,
                '[{"q":"What should you do when a customer is not available?","options":["Leave without informing","Call the customer","Return to dark store","Wait indefinitely"],"answer":1}]',TRUE),
                ('cccccccc-0000-0000-0000-000000000003','Helmet and Safety Gear',       'हेलमेट और सुरक्षा',    'https://yana-skills.s3.ap-south-1.amazonaws.com/videos/safety-gear.mp4',360,1,20,TRUE,
                '[{"q":"When must you wear a helmet?","options":["Only on highways","Always while riding","Only in heavy traffic","Never"],"answer":1},{"q":"What is the speed limit in residential areas?","options":["80 kmph","60 kmph","40 kmph","20 kmph"],"answer":2}]',TRUE),
                ('cccccccc-0000-0000-0000-000000000004','Charging Your EV Scooter',     'ईवी स्कूटर चार्ज करें','https://yana-skills.s3.ap-south-1.amazonaws.com/videos/ev-charging.mp4',300,1,15,FALSE,NULL,TRUE)
            ON CONFLICT DO NOTHING;
            """,
            reverse_sql="""
            DROP TABLE IF EXISTS rider_badges CASCADE;
            DROP TABLE IF EXISTS rider_gamification CASCADE;
            DROP TABLE IF EXISTS rider_skill_progress CASCADE;
            DROP TABLE IF EXISTS skill_videos CASCADE;
            DROP TABLE IF EXISTS skill_modules CASCADE;
            """
        ),
    ]
