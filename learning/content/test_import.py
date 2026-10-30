from io import StringIO
from unittest.mock import patch

from django.core.management.base import CommandError
from django.test import TestCase

from learning.management.commands.import_rust_content import Command
from learning.models import Chapter, Choice, Course, Exercise, Lesson, Question, Quiz


class RustContentImportTests(TestCase):
    def run_import(self):
        Command(stdout=StringIO()).handle()

    def test_idempotent_and_conflict_rolls_back(self):
        self.run_import()
        models = (Course, Chapter, Lesson, Exercise, Quiz, Question, Choice)
        counts = [model.objects.count() for model in models]
        self.run_import()
        self.assertEqual(counts, [model.objects.count() for model in models])

        exercise = Exercise.objects.get(slug="check-version")
        exercise.delete()
        lesson = Lesson.objects.get(slug="loop-and-errors")
        lesson.title = "ویرایش مدیر"
        lesson.save(update_fields=["title"])
        with self.assertRaises(CommandError):
            self.run_import()
        self.assertFalse(Exercise.objects.filter(slug="check-version").exists())
        lesson.refresh_from_db()
        self.assertEqual(lesson.title, "ویرایش مدیر")

    def test_missing_version_does_not_import(self):
        with patch("learning.management.commands.import_rust_content.CONTENT") as content:
            content.read_text.return_value = '{"course": {"slug": "rust", "title": "Rust", "published": true, "chapters": []}}'
            with self.assertRaises(CommandError):
                self.run_import()
        self.assertFalse(Course.objects.exists())

    def test_one_correct_choice_per_question(self):
        self.run_import()
        for question in Question.objects.all():
            self.assertEqual(question.choices.filter(is_correct=True).count(), 1)
