from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST, require_safe

from learning.models import Lesson

from .models import LessonProgress, QuizAttempt


@login_required
@require_safe
def dashboard(request):
    lessons = LessonProgress.objects.filter(user=request.user).select_related("lesson__chapter__course").order_by("-completed_at")
    attempts = QuizAttempt.objects.filter(user=request.user).select_related("quiz__chapter__course")
    return render(request, "progress/dashboard.html", {"lessons": lessons, "attempts": attempts})


@login_required
@require_POST
def complete(request, course_slug, chapter_slug, lesson_slug):
    lesson = get_object_or_404(
        Lesson, slug=lesson_slug, published=True, chapter__slug=chapter_slug,
        chapter__published=True, chapter__course__slug=course_slug, chapter__course__published=True,
    )
    LessonProgress.objects.get_or_create(user=request.user, lesson=lesson)
    return redirect("progress:list")
