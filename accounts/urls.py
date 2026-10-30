from functools import wraps

from allauth.socialaccount.models import SocialApp
from allauth.socialaccount.providers.google import views as google_views
from django.http import Http404
from django.urls import include, path


def require_google_app(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        try:
            return view(request, *args, **kwargs)
        except SocialApp.DoesNotExist as exc:
            raise Http404 from exc

    return wrapped


urlpatterns = [
    path("google/login/", require_google_app(google_views.oauth2_login), name="google_login"),
    path("google/login/callback/", require_google_app(google_views.oauth2_callback), name="google_callback"),
    path("google/login/token/", require_google_app(google_views.login_by_token), name="google_login_by_token"),
    path("", include("allauth.urls")),
]
