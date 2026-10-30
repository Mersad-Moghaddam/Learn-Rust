from django.urls import path

from . import views

app_name = "learning"
urlpatterns = [
    path("", views.index, name="index"),
    path("<slug:course_slug>/<slug:chapter_slug>/lessons/<slug:lesson_slug>/", views.lesson, name="lesson"),
    path("<slug:course_slug>/<slug:chapter_slug>/quiz/", views.quiz, name="quiz"),
]
