"""tests/test_skills.py — Skills & Gamification tests"""
import json, uuid
from django.test import TestCase, Client
from skills_service.core.models import SkillModule, SkillVideo, RiderGamification, RiderBadge
from skills_service.core.services import (
    get_or_create_gamification, award_points, record_video_watch,
    submit_quiz, get_onboarding_readiness,
)


def admin_token(role="SUPER_ADMIN"):
    import jwt
    from django.conf import settings
    return f"Bearer {jwt.encode({'user_id':str(uuid.uuid4()),'role':role,'token_type':'admin','type':'access'}, settings.JWT_SECRET_KEY, algorithm='HS256')}"

def rider_token(rider_id):
    import jwt
    from django.conf import settings
    return f"Bearer {jwt.encode({'user_id':str(rider_id),'role':'RIDER','token_type':'rider','type':'access'}, settings.JWT_SECRET_KEY, algorithm='HS256')}"


def make_module(mandatory=True, published=True):
    return SkillModule.objects.create(
        title="Test Module", is_mandatory=mandatory, is_published=published, sequence_order=1,
    )

def make_video(module, points=10, has_quiz=False, quiz_questions=None):
    return SkillVideo.objects.create(
        module=module, title="Test Video",
        video_url="http://example.com/video.mp4",
        duration_secs=300, sequence_order=1,
        points_reward=points, has_quiz=has_quiz,
        quiz_questions=quiz_questions, is_published=True,
    )


class GamificationTest(TestCase):

    def setUp(self):
        self.rider_id = str(uuid.uuid4())
        self.g = get_or_create_gamification(self.rider_id)

    def test_initial_state(self):
        self.assertEqual(self.g.total_points, 0)
        self.assertEqual(self.g.current_level, 1)

    def test_award_points_increases_total(self):
        g = award_points(self.rider_id, 50, "test")
        self.assertEqual(g.total_points, 50)

    def test_level_up(self):
        # Level thresholds: [0, 100, 300, 600, 1000, 1500, 2500]
        g = award_points(self.rider_id, 100, "test")
        self.assertEqual(g.current_level, 2)  # >= 100 = level 2

    def test_multiple_awards_accumulate(self):
        award_points(self.rider_id, 50, "a")
        g = award_points(self.rider_id, 60, "b")  # 110 total
        self.assertEqual(g.total_points, 110)
        self.assertEqual(g.current_level, 2)

    def test_badge_awarded_on_level3(self):
        award_points(self.rider_id, 300, "level3")
        badges = RiderBadge.objects.filter(rider_id=self.rider_id)
        self.assertTrue(badges.filter(badge_code="QUICK_LEARNER").exists())


class VideoProgressTest(TestCase):

    def setUp(self):
        self.rider_id = str(uuid.uuid4())
        get_or_create_gamification(self.rider_id)
        self.module = make_module()
        self.video  = make_video(self.module, points=15)

    def test_watch_video_creates_progress(self):
        progress = record_video_watch(self.rider_id, str(self.video.id), 150, False)
        self.assertEqual(progress.watch_time_secs, 150)
        self.assertFalse(progress.is_completed)

    def test_complete_video_awards_points(self):
        record_video_watch(self.rider_id, str(self.video.id), 300, True)
        g = RiderGamification.objects.get(rider_id=self.rider_id)
        self.assertEqual(g.total_points, 15)

    def test_complete_video_twice_no_double_points(self):
        record_video_watch(self.rider_id, str(self.video.id), 300, True)
        record_video_watch(self.rider_id, str(self.video.id), 300, True)
        g = RiderGamification.objects.get(rider_id=self.rider_id)
        self.assertEqual(g.total_points, 15)  # Points only once

    def test_quiz_pass_awards_bonus(self):
        q_video = make_video(self.module, has_quiz=True,
            quiz_questions=[{"q": "Q1?", "options": ["A","B","C","D"], "answer": 0}])
        result = submit_quiz(self.rider_id, str(q_video.id), [0])
        self.assertTrue(result["passed"])
        self.assertGreater(result["points_awarded"], 0)

    def test_quiz_fail_no_bonus(self):
        q_video = make_video(self.module, has_quiz=True,
            quiz_questions=[
                {"q":"Q1?","options":["A","B","C","D"],"answer":0},
                {"q":"Q2?","options":["A","B","C","D"],"answer":1},
            ])
        result = submit_quiz(self.rider_id, str(q_video.id), [1, 0])  # Both wrong
        self.assertFalse(result["passed"])
        self.assertEqual(result["points_awarded"], 0)

    def test_onboarding_readiness_all_complete(self):
        record_video_watch(self.rider_id, str(self.video.id), 300, True)
        data = get_onboarding_readiness(self.rider_id)
        self.assertEqual(data["total_mandatory"], 1)
        self.assertTrue(data["all_mandatory_complete"])


class SkillsAPITest(TestCase):

    def setUp(self):
        self.client   = Client()
        self.admin    = admin_token()
        self.rider_id = str(uuid.uuid4())
        self.rtok     = rider_token(self.rider_id)

    def test_list_modules_rider_sees_published(self):
        SkillModule.objects.create(title="Published", is_mandatory=True, is_published=True, sequence_order=1)
        SkillModule.objects.create(title="Draft",     is_mandatory=False, is_published=False, sequence_order=2)
        resp = self.client.get("/api/v1/skills/modules/", HTTP_AUTHORIZATION=self.rtok)
        self.assertEqual(resp.status_code, 200)
        titles = [r["title"] for r in resp.json()["data"]["results"]]
        self.assertIn("Published", titles)
        self.assertNotIn("Draft", titles)

    def test_create_module_admin(self):
        resp = self.client.post("/api/v1/skills/modules/",
            data=json.dumps({"title":"New Module","is_mandatory":True,"sequence_order":1}),
            content_type="application/json", HTTP_AUTHORIZATION=admin_token("HUB_OPS"))
        self.assertEqual(resp.status_code, 201)

    def test_leaderboard(self):
        get_or_create_gamification(self.rider_id)
        award_points(self.rider_id, 100, "test")
        resp = self.client.get("/api/v1/skills/leaderboard/", HTTP_AUTHORIZATION=self.rtok)
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.json()["data"]["leaderboard"]), 1)

    def test_gamification_endpoint(self):
        get_or_create_gamification(self.rider_id)
        resp = self.client.get(f"/api/v1/skills/riders/{self.rider_id}/gamification/",
                               HTTP_AUTHORIZATION=self.rtok)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("total_points", resp.json()["data"])
