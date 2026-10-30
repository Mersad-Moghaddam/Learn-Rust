from django.contrib import admin

from .models import Chapter, Choice, Course, Exercise, Lesson, Question, Quiz


admin.site.register([Course, Chapter, Lesson, Exercise, Quiz, Question, Choice])
