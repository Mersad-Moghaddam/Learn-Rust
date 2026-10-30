from django.core.exceptions import ValidationError
from django.db import transaction

from .models import QuizAttempt


@transaction.atomic
def submit_quiz(user, quiz, snapshot):
    """Persist the server-evaluated snapshot returned by learning.evaluate_quiz."""
    if not user.is_authenticated or snapshot.get("quiz_id") != quiz.pk:
        raise ValidationError("ثبت نتیجه آزمون معتبر نیست.")
    if not (quiz.published and quiz.chapter.published and quiz.chapter.course.published):
        raise ValidationError("این آزمون منتشر نشده است.")
    return QuizAttempt.objects.create(user=user, quiz=quiz, snapshot=snapshot)
