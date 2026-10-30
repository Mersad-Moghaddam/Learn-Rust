from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.http import QueryDict
from django.db import DatabaseError, close_old_connections, connection, transaction
from django.test import TestCase, TransactionTestCase, override_settings, skipUnlessDBFeature
from django.urls import reverse

from .models import Chapter, Choice, Course, Lesson, Question, Quiz
from .services import evaluate_quiz
from .content.test_import import RustContentImportTests  # Ensure Django's test discovery includes content import tests.


@override_settings(ROOT_URLCONF="learning.tests_urls")
class PublicLearningTests(TestCase):
    def setUp(self):
        self.course = Course.objects.create(slug="rust", title="Rust", published=True)
        self.chapter = Chapter.objects.create(course=self.course, slug="first", title="First", order=1, published=True)
        self.lesson = Lesson.objects.create(chapter=self.chapter, slug="hello", title="Hello", body="Body", order=1, published=True)
        self.quiz = Quiz.objects.create(chapter=self.chapter, slug="quiz", title="Quiz", published=True)
        self.question = Question.objects.create(quiz=self.quiz, slug="q", prompt="Question", order=1)
        self.choice = Choice.objects.create(question=self.question, slug="a", text="Answer", is_correct=True, order=1)

    def test_unpublished_ancestor_hides_lesson_and_quiz(self):
        self.chapter.published = False
        self.chapter.save()
        self.assertEqual(self.client.get(reverse("learning:lesson", args=["rust", "first", "hello"])).status_code, 404)
        self.assertEqual(self.client.get(reverse("learning:quiz", args=["rust", "first"])).status_code, 404)
        self.assertNotContains(self.client.get(reverse("learning:index")), "Hello")

    def test_index_does_not_query_each_chapters_quiz(self):
        for number in range(3):
            Chapter.objects.create(course=self.course, slug=f"chapter-{number}", title="Chapter", published=True)
        with self.assertNumQueries(3):
            response = self.client.get(reverse("learning:index"))
        self.assertContains(response, "آزمون First")

    def test_quiz_requires_login_for_submission(self):
        response = self.client.post(reverse("learning:quiz", args=["rust", "first"]), {str(self.question.pk): str(self.choice.pk)})
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_quiz_submission_calls_progress_service(self):
        user = get_user_model().objects.create_user(email="user@example.com", password="a-test-password")
        self.client.force_login(user)
        with patch("progress.services.submit_quiz") as submit:
            response = self.client.post(reverse("learning:quiz", args=["rust", "first"]), {str(self.question.pk): str(self.choice.pk)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(submit.call_args.args[:2], (user, self.quiz))
        snapshot = submit.call_args.args[2]
        self.assertEqual(snapshot["score"], 1)
        self.assertEqual(snapshot["answers"][0]["choice_id"], self.choice.pk)
        self.assertContains(response, "پاسخ صحیح")

    def test_answers_are_not_disclosed_before_submission(self):
        self.question.explanation = "توضیح محرمانه"
        self.question.save()
        response = self.client.get(reverse("learning:quiz", args=["rust", "first"]))
        self.assertNotContains(response, "توضیح محرمانه")
        self.assertNotContains(response, "پاسخ صحیح")

    def test_evaluation_rejects_missing_foreign_and_duplicate_answers(self):
        other = Question.objects.create(quiz=self.quiz, slug="other", prompt="Other")
        foreign = Choice.objects.create(question=other, slug="other", text="Other", is_correct=True)
        for answers in ({}, {str(self.question.pk): str(foreign.pk)}, QueryDict(f"{self.question.pk}={self.choice.pk}&{self.question.pk}={self.choice.pk}")):
            with self.subTest(answers=answers), self.assertRaises(ValidationError):
                evaluate_quiz(self.quiz, answers)

    def test_duplicate_answer_is_rejected_for_complete_submission(self):
        answers = QueryDict(f"{self.question.pk}={self.choice.pk}&{self.question.pk}={self.choice.pk}")
        with self.assertRaises(ValidationError):
            evaluate_quiz(self.quiz, answers)

    def test_snapshot_preserves_answer_text_and_explanation(self):
        self.question.explanation = "Explanation"
        self.question.save()
        snapshot = evaluate_quiz(self.quiz, {str(self.question.pk): str(self.choice.pk)})
        self.choice.text = "Changed"
        self.choice.save()
        self.assertEqual(snapshot["answers"][0]["correct_choice_text"], "Answer")
        self.assertEqual(snapshot["answers"][0]["explanation"], "Explanation")

    def test_evaluation_ignores_stale_prefetch_and_quiz_fields(self):
        quiz = Quiz.objects.prefetch_related("questions__choices").get(pk=self.quiz.pk)
        list(quiz.questions.all())
        Choice.objects.filter(pk=self.choice.pk).update(text="Updated")
        Quiz.objects.filter(pk=quiz.pk).update(title="Updated quiz")
        snapshot = evaluate_quiz(quiz, {str(self.question.pk): str(self.choice.pk)})
        self.assertEqual(snapshot["quiz_title"], "Updated quiz")
        self.assertEqual(snapshot["answers"][0]["choice_text"], "Updated")

    def test_invalid_configuration_is_rejected(self):
        Choice.objects.create(question=self.question, slug="b", text="B", is_correct=True)
        with self.assertRaises(ValidationError):
            evaluate_quiz(self.quiz, {str(self.question.pk): str(self.choice.pk)})


class IntegratedQuizTests(TestCase):
    def test_submission_requires_csrf_and_saves_only_for_submitter(self):
        from django.test import Client
        from progress.models import QuizAttempt

        course = Course.objects.create(slug="rust", title="Rust", published=True)
        chapter = Chapter.objects.create(course=course, slug="first", title="First", published=True)
        quiz = Quiz.objects.create(chapter=chapter, slug="quiz", title="Quiz", published=True)
        question = Question.objects.create(quiz=quiz, slug="q", prompt="Question")
        choice = Choice.objects.create(question=question, slug="a", text="Answer", is_correct=True)
        user = get_user_model().objects.create_user(email="submitter@example.com", password="a-test-password")
        other = get_user_model().objects.create_user(email="other@example.com", password="a-test-password")
        client = Client(enforce_csrf_checks=True)
        client.force_login(user)
        url = reverse("learning:quiz", args=["rust", "first"])
        self.assertEqual(client.post(url, {str(question.pk): str(choice.pk)}).status_code, 403)
        self.assertFalse(QuizAttempt.objects.exists())
        client.get(url)
        response = client.post(url, {str(question.pk): str(choice.pk),
                                     "csrfmiddlewaretoken": client.cookies["csrftoken"].value})
        self.assertEqual(response.status_code, 200)
        attempt = QuizAttempt.objects.get()
        self.assertEqual(attempt.user, user)
        self.assertEqual(attempt.snapshot["score"], 1)
        client.force_login(other)
        self.assertNotContains(client.get(reverse("progress:list")), "Question")
        course.published = False
        course.save(update_fields=["published"])
        self.assertEqual(client.get(url).status_code, 404)


@override_settings(ROOT_URLCONF="learning.tests_urls")
class QuizLockTests(TransactionTestCase):
    @skipUnlessDBFeature("has_select_for_update_nowait")
    def test_submission_holds_content_locks_until_attempt_is_saved(self):
        course = Course.objects.create(slug="rust", title="Rust", published=True)
        chapter = Chapter.objects.create(course=course, slug="first", title="First", published=True)
        quiz = Quiz.objects.create(chapter=chapter, slug="quiz", title="Quiz", published=True)
        question = Question.objects.create(quiz=quiz, slug="q", prompt="Question")
        choice = Choice.objects.create(question=question, slug="a", text="Answer", is_correct=True)
        user = get_user_model().objects.create_user(email="lock@example.com", password="a-test-password")
        self.client.force_login(user)

        def check_locks():
            close_old_connections()
            try:
                for model, pk in ((Course, course.pk), (Chapter, chapter.pk), (Quiz, quiz.pk),
                                  (Question, question.pk), (Choice, choice.pk)):
                    with self.assertRaises(DatabaseError), transaction.atomic():
                        model.objects.select_for_update(nowait=True).get(pk=pk)
            finally:
                connection.close()

        def submit(*args):
            with ThreadPoolExecutor(max_workers=1) as executor:
                executor.submit(check_locks).result(timeout=10)
            return None

        with patch("progress.services.submit_quiz", side_effect=submit):
            response = self.client.post(reverse("learning:quiz", args=["rust", "first"]),
                                        {str(question.pk): str(choice.pk)})
        self.assertEqual(response.status_code, 200)
