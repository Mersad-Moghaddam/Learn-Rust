import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction

from learning.models import Chapter, Choice, Course, Exercise, Lesson, Question, Quiz


CONTENT = Path(__file__).resolve().parents[2] / "content" / "rust_v1.json"


class Command(BaseCommand):
    help = "Import versioned Rust content without overwriting existing edits."

    def handle(self, *args, **options):
        try:
            data = json.loads(CONTENT.read_text(encoding="utf-8"))
            version = data["version"]
            with transaction.atomic():
                self.import_content(data)
        except (OSError, ValueError, KeyError, IntegrityError) as exc:
            raise CommandError(f"Rust content import failed: {exc}") from exc
        self.stdout.write(self.style.SUCCESS(f"Rust content v{version} imported."))

    def import_content(self, data):
        def put(model, parent, values, children=()):
            fields = {key: value for key, value in values.items() if key not in children and key != "slug"}
            lookup = {**parent, "slug": values["slug"]}
            obj, created = model.objects.select_for_update().get_or_create(**lookup, defaults=fields)
            if not created:
                changed = [key for key, value in fields.items() if getattr(obj, key) != value]
                if changed:
                    raise CommandError(
                        f"Conflict in {model.__name__} {values['slug']}: {', '.join(changed)}. "
                        "Existing content was not changed."
                    )
            return obj

        course_data = data["course"]
        course = put(Course, {}, course_data, ("chapters",))
        for chapter_data in course_data["chapters"]:
            chapter = put(Chapter, {"course": course}, chapter_data, ("lessons", "quiz"))
            for lesson_data in chapter_data["lessons"]:
                lesson = put(Lesson, {"chapter": chapter}, lesson_data, ("exercises",))
                for exercise in lesson_data["exercises"]:
                    put(Exercise, {"lesson": lesson}, exercise)
            quiz_data = chapter_data["quiz"]
            existing_quiz = Quiz.objects.select_for_update().filter(chapter=chapter).first()
            if existing_quiz and existing_quiz.slug != quiz_data["slug"]:
                raise CommandError(f"Conflict: chapter {chapter.slug} already has quiz {existing_quiz.slug}.")
            quiz = put(Quiz, {"chapter": chapter}, quiz_data, ("questions",))
            for question_data in quiz_data["questions"]:
                question = put(Question, {"quiz": quiz}, question_data, ("choices",))
                for choice in question_data["choices"]:
                    put(Choice, {"question": question}, choice)
