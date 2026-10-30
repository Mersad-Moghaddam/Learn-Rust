from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Prefetch

from .models import Choice, Quiz


@transaction.atomic
def evaluate_quiz(quiz, answers):
    """Validate single-choice answers and return a JSON-serializable result snapshot.

    Keys in answers are question primary keys; values are choice primary keys.
    Progress should store the returned snapshot alongside each attempt.
    """
    quiz = Quiz.objects.select_for_update().select_related("chapter__course").get(pk=quiz.pk)
    if not (quiz.published and quiz.chapter.published and quiz.chapter.course.published):
        raise ValidationError("این آزمون منتشر نشده است.")
    questions = list(quiz.questions.select_for_update().prefetch_related(
        Prefetch("choices", queryset=Choice.objects.select_for_update())
    ))
    if not questions:
        raise ValidationError("این آزمون هنوز پرسشی ندارد.")

    results = []
    for question in questions:
        choices = list(question.choices.all())
        correct = [choice for choice in choices if choice.is_correct]
        if len(correct) != 1:
            raise ValidationError("این آزمون به‌درستی تنظیم نشده است.")
        key = str(question.pk)
        values = answers.getlist(key) if hasattr(answers, "getlist") else [answers.get(key)]
        if len(values) != 1:
            raise ValidationError("برای هر پرسش یک پاسخ انتخاب کنید.")
        selected = next((choice for choice in choices if str(choice.pk) == str(values[0])), None)
        if selected is None:
            raise ValidationError("برای هر پرسش یک پاسخ معتبر انتخاب کنید.")
        results.append({
            "question_id": question.pk,
            "question_slug": question.slug,
            "prompt": question.prompt,
            "choice_id": selected.pk,
            "choice_slug": selected.slug,
            "choice_text": selected.text,
            "correct_choice_id": correct[0].pk,
            "correct_choice_slug": correct[0].slug,
            "correct_choice_text": correct[0].text,
            "is_correct": selected.pk == correct[0].pk,
            "explanation": question.explanation,
        })
    return {
        "quiz_id": quiz.pk,
        "quiz_slug": quiz.slug,
        "quiz_title": quiz.title,
        "score": sum(result["is_correct"] for result in results),
        "total": len(results),
        "answers": results,
    }
