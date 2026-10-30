from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from learning.models import Chapter, Choice, Course, Lesson, Question, Quiz
from learning.services import evaluate_quiz

from .models import LessonProgress, QuizAttempt
from .services import submit_quiz


class ProgressTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(email="one@example.com", password="test-password")
        self.other = get_user_model().objects.create_user(email="two@example.com", password="test-password")
        self.course = Course.objects.create(slug="rust", title="Rust", published=True)
        self.chapter = Chapter.objects.create(course=self.course, slug="first", title="First", published=True)
        self.lesson = Lesson.objects.create(chapter=self.chapter, slug="hello", title="Hello", body="Body", published=True)
        self.quiz = Quiz.objects.create(chapter=self.chapter, slug="quiz", title="Quiz", published=True)
        self.question = Question.objects.create(quiz=self.quiz, slug="q", prompt="Original question")
        self.choice = Choice.objects.create(question=self.question, slug="a", text="Original answer", is_correct=True)
        self.complete_url = reverse("progress:complete", args=["rust", "first", "hello"])

    @override_settings(ROOT_URLCONF="config.urls")
    def test_user_can_find_and_record_progress_from_learning_pages(self):
        lesson_url = reverse("learning:lesson", args=["rust", "first", "hello"])
        quiz_url = reverse("learning:quiz", args=["rust", "first"])
        self.assertContains(self.client.get(lesson_url), reverse("account_login"))
        self.assertContains(self.client.get(quiz_url), reverse("account_login"))
        self.client.force_login(self.user)
        self.assertContains(self.client.get(reverse("learning:index")), reverse("progress:list"))
        lesson_page = self.client.get(lesson_url)
        self.assertContains(lesson_page, self.complete_url)
        self.assertContains(lesson_page, "csrfmiddlewaretoken")
        self.assertFalse(LessonProgress.objects.exists())
        self.assertRedirects(self.client.post(self.complete_url), reverse("progress:list"))
        self.assertContains(self.client.get(reverse("progress:list")), "Hello")
        self.assertContains(self.client.get(quiz_url), reverse("progress:list"))

    def test_login_post_csrf_and_publication_required(self):
        self.assertEqual(self.client.get(reverse("progress:list")).status_code, 302)
        self.assertEqual(self.client.post(self.complete_url).status_code, 302)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.complete_url).status_code, 405)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        self.assertEqual(csrf_client.post(self.complete_url).status_code, 403)
        self.course.published = False
        self.course.save()
        self.assertEqual(self.client.post(self.complete_url).status_code, 404)
        self.assertFalse(LessonProgress.objects.exists())

    def test_completion_is_explicit_idempotent_and_unique(self):
        self.client.force_login(self.user)
        self.client.get(reverse("learning:lesson", args=["rust", "first", "hello"]))
        self.assertFalse(LessonProgress.objects.exists())
        self.client.post(self.complete_url)
        self.client.post(self.complete_url)
        self.assertEqual(LessonProgress.objects.filter(user=self.user, lesson=self.lesson).count(), 1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            LessonProgress.objects.create(user=self.user, lesson=self.lesson)

    def test_dashboard_only_shows_owner_and_snapshot_survives_edits(self):
        snapshot = evaluate_quiz(self.quiz, {str(self.question.pk): str(self.choice.pk)})
        submit_quiz(self.user, self.quiz, snapshot)
        LessonProgress.objects.create(user=self.other, lesson=self.lesson)
        self.question.prompt = "Changed question"
        self.question.save()
        self.client.force_login(self.user)
        response = self.client.get(reverse("progress:list"))
        self.assertContains(response, "Original question")
        self.assertNotContains(response, "Changed question")
        self.assertNotContains(response, "Hello")
        self.client.force_login(self.other)
        response = self.client.get(reverse("progress:list"))
        self.assertContains(response, "Hello")
        self.assertNotContains(response, "Original question")

    def test_quiz_submission_integration_and_invalid_snapshot(self):
        self.client.force_login(self.user)
        url = reverse("learning:quiz", args=["rust", "first"])
        self.assertEqual(self.client.post(url, {str(self.question.pk): str(self.choice.pk)}).status_code, 200)
        attempt = QuizAttempt.objects.get(user=self.user)
        self.assertEqual(attempt.snapshot["score"], 1)
        with self.assertRaises(ValidationError):
            submit_quiz(self.user, self.quiz, {"quiz_id": -1})
        self.assertEqual(QuizAttempt.objects.count(), 1)
