from django.urls import include, path

urlpatterns = [path("progress/", include("progress.urls")), path("learn/", include("learning.urls"))]
