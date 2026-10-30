from config.settings import *  # noqa: F403


AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 3
SOCIALACCOUNT_PROVIDERS = {"google": {"APP": {"client_id": "test-client", "secret": "test-secret"}}}
SOCIALACCOUNT_EMAIL_AUTHENTICATION = False
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = False
ROOT_URLCONF = "accounts.test_urls"
LOGIN_REDIRECT_URL = "/"
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
ALLOWED_HOSTS = ["testserver"]
TEMPLATES[0]["OPTIONS"]["loaders"] = [  # noqa: F405
    ("django.template.loaders.locmem.Loader", {"base.html": "{% block content %}{% endblock %}"}),
    "django.template.loaders.app_directories.Loader",
]
TEMPLATES[0]["APP_DIRS"] = False  # noqa: F405
