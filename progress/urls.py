from django.urls import path

from . import views

app_name = "progress"

urlpatterns = [
    path("", views.dashboard, name="list"),
    path("<slug:course_slug>/<slug:chapter_slug>/<slug:lesson_slug>/complete/", views.complete, name="complete"),
]
