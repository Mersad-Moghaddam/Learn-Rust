from django.db import models


class Course(models.Model):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=200)
    published = models.BooleanField(default=False)

    def __str__(self):
        return self.title


class Chapter(models.Model):
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="chapters")
    slug = models.SlugField()
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)
    published = models.BooleanField(default=False)

    class Meta:
        ordering = ["order", "pk"]
        constraints = [models.UniqueConstraint(fields=["course", "slug"], name="learning_chapter_course_slug_uniq")]

    def __str__(self):
        return self.title


class Lesson(models.Model):
    chapter = models.ForeignKey(Chapter, on_delete=models.PROTECT, related_name="lessons")
    slug = models.SlugField()
    title = models.CharField(max_length=200)
    body = models.TextField()
    code = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    published = models.BooleanField(default=False)

    class Meta:
        ordering = ["order", "pk"]
        constraints = [models.UniqueConstraint(fields=["chapter", "slug"], name="learning_lesson_chapter_slug_uniq")]

    def __str__(self):
        return self.title


class Exercise(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.PROTECT, related_name="exercises")
    slug = models.SlugField()
    title = models.CharField(max_length=200)
    instructions = models.TextField()
    starter_code = models.TextField(blank=True)
    hint = models.TextField(blank=True)
    answer = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "pk"]
        constraints = [models.UniqueConstraint(fields=["lesson", "slug"], name="learning_exercise_lesson_slug_uniq")]

    def __str__(self):
        return self.title


class Quiz(models.Model):
    chapter = models.OneToOneField(Chapter, on_delete=models.PROTECT, related_name="quiz")
    slug = models.SlugField()
    title = models.CharField(max_length=200)
    published = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["chapter", "slug"], name="learning_quiz_chapter_slug_uniq")]

    def __str__(self):
        return self.title


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.PROTECT, related_name="questions")
    slug = models.SlugField()
    prompt = models.TextField()
    explanation = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "pk"]
        constraints = [models.UniqueConstraint(fields=["quiz", "slug"], name="learning_question_quiz_slug_uniq")]

    def __str__(self):
        return self.prompt


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.PROTECT, related_name="choices")
    slug = models.SlugField()
    text = models.TextField()
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "pk"]
        constraints = [models.UniqueConstraint(fields=["question", "slug"], name="learning_choice_question_slug_uniq")]

    def __str__(self):
        return self.text
