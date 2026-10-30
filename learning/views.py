from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods, require_safe

from .models import Chapter, Course, Lesson, Quiz
from .services import evaluate_quiz


@require_safe
def index(request):
    chapters = Chapter.objects.filter(published=True).select_related("quiz").prefetch_related(
        Prefetch("lessons", queryset=Lesson.objects.filter(published=True))
    )
    courses = Course.objects.filter(published=True).prefetch_related(Prefetch("chapters", queryset=chapters))
    return render(request, "learning/index.html", {"courses": courses})


@require_safe
def lesson(request, course_slug, chapter_slug, lesson_slug):
    item = get_object_or_404(
        Lesson.objects.select_related("chapter__course").prefetch_related("exercises"),
        slug=lesson_slug, published=True, chapter__slug=chapter_slug,
        chapter__published=True, chapter__course__slug=course_slug, chapter__course__published=True,
    )
    return render(request, "learning/lesson.html", {"lesson": item})


@require_http_methods(["GET", "POST"])
@transaction.atomic
def quiz(request, course_slug, chapter_slug):
    queryset = Quiz.objects.select_related("chapter__course")
    if request.method == "POST":
        queryset = queryset.select_for_update()
    else:
        queryset = queryset.prefetch_related("questions__choices")
    item = get_object_or_404(
        queryset,
        published=True, chapter__slug=chapter_slug, chapter__published=True,
        chapter__course__slug=course_slug, chapter__course__published=True,
    )
    context = {"quiz": item}
    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        from progress.services import submit_quiz

        try:
            result = evaluate_quiz(item, request.POST)
            context["attempt"] = submit_quiz(request.user, item, result)
            context["result"] = result
        except ValidationError as error:
            context["errors"] = error.messages
            return render(request, "learning/quiz.html", context, status=400)
    return render(request, "learning/quiz.html", context)
