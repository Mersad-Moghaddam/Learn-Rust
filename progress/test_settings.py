from config.settings import *  # noqa: F403


if os.environ.get("PROGRESS_TEST_SQLITE") == "1":  # noqa: F405
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
ROOT_URLCONF = "progress.test_urls"
ALLOWED_HOSTS = ["testserver"]
TEMPLATES[0]["OPTIONS"]["loaders"] = [  # noqa: F405
    ("django.template.loaders.locmem.Loader", {"base.html": "{% block content %}{% endblock %}"}),
    "django.template.loaders.app_directories.Loader",
]
TEMPLATES[0]["APP_DIRS"] = False  # noqa: F405
