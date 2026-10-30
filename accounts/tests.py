from unittest.mock import patch

import re

from django.core import mail
from django.db import IntegrityError, connection, transaction
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from allauth.account.models import EmailAddress

from .models import User


class UserManagerTests(SimpleTestCase):
    def test_email_user_and_superuser(self):
        with patch.object(User, "save"):
            user = User.objects.create_user("person@EXAMPLE.COM", "secret")
            self.assertEqual(user.email, "person@example.com")
            self.assertTrue(user.check_password("secret"))
            self.assertFalse(user.is_staff)
            admin = User.objects.create_superuser("admin@example.com", "secret")
            self.assertTrue(admin.is_staff and admin.is_superuser)
        with self.assertRaises(ValueError):
            User.objects.create_user("", "secret")
        with self.assertRaises(ValueError):
            User.objects.create_superuser("admin@example.com", "secret", is_staff=False)


class EmailConstraintTests(TestCase):
    def test_conditional_uniqueness_on_insert_and_update(self):
        first = User.objects.create_user("first@example.com")
        second = User.objects.create_user("second@example.com")
        third = User.objects.create_user("third@example.com")
        EmailAddress.objects.create(user=first, email="shared@example.com", verified=True, primary=True)
        pending = EmailAddress.objects.create(user=second, email="shared@example.com")
        other = EmailAddress.objects.create(user=first, email="other@example.com")
        EmailAddress.objects.create(user=second, email="another@example.com")

        for address, field in ((pending, "verified"), (other, "primary")):
            with self.subTest(field=field), self.assertRaises(IntegrityError), transaction.atomic():
                EmailAddress.objects.filter(pk=address.pk).update(**{field: True})
        for user, email, flags in (
            (third, "shared@example.com", {"verified": True}),
            (first, "third@example.com", {"primary": True}),
        ):
            with self.subTest(flags=flags), self.assertRaises(IntegrityError), transaction.atomic():
                EmailAddress.objects.create(user=user, email=email, **flags)

    def test_mysql_indexes_exist(self):
        if connection.vendor != "mysql":
            self.skipTest("MySQL-specific indexes")
        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(cursor, "account_emailaddress")
        for name in ("accounts_unique_verified_email", "accounts_unique_primary_user"):
            self.assertTrue(constraints[name]["unique"])


class IdentityFlowTests(TestCase):
    def setUp(self):
        from django.core.cache import cache

        cache.clear()

    def test_google_button_only_when_configured(self):
        for page in ("account_login", "account_signup"):
            with override_settings(SOCIALACCOUNT_PROVIDERS={"google": {"APP": {
                "client_id": "test-client", "secret": "test-secret",
            }}}):
                self.assertContains(self.client.get(reverse(page)), reverse("google_login"))
            with override_settings(SOCIALACCOUNT_PROVIDERS={}):
                response = self.client.get(reverse(page))
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, reverse("google_login"))

    @override_settings(SOCIALACCOUNT_PROVIDERS={})
    def test_unconfigured_google_endpoints_return_404(self):
        for name in ("google_login", "google_callback", "google_login_by_token"):
            for method in (self.client.get, self.client.post):
                self.assertEqual(method(reverse(name)).status_code, 404)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_signup_verification_and_login(self):
        response = self.client.post(reverse("account_signup"), {
            "email": "person@example.com", "password1": "strong-pass-564!", "password2": "strong-pass-564!",
        })
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(email="person@example.com")
        self.assertFalse(EmailAddress.objects.get(user=user).verified)
        self.assertNotIn("_auth_user_id", self.client.session)
        link = re.search(r"https?://[^\s]+/accounts/confirm-email/[^\s]+", mail.outbox[0].body).group()
        self.assertEqual(self.client.get(link).status_code, 200)
        self.assertFalse(EmailAddress.objects.get(user=user).verified)
        self.client.post(link)
        self.assertTrue(EmailAddress.objects.get(user=user).verified)
        self.client.post(reverse("account_login"), {"login": user.email, "password": "strong-pass-564!"})
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_unverified_and_inactive_users_cannot_log_in(self):
        user = User.objects.create_user("person@example.com", "strong-pass-564!")
        address = EmailAddress.objects.create(user=user, email=user.email, primary=True)
        credentials = {"login": user.email, "password": "strong-pass-564!"}
        self.client.post(reverse("account_login"), credentials)
        self.assertNotIn("_auth_user_id", self.client.session)
        address.verified = True
        address.save()
        user.is_active = False
        user.save()
        self.client.post(reverse("account_login"), credentials)
        self.assertNotIn("_auth_user_id", self.client.session)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_confirmation_requires_csrf_and_rejects_invalid_keys(self):
        from django.test import Client

        self.client.post(reverse("account_signup"), {
            "email": "person@example.com", "password1": "strong-pass-564!", "password2": "strong-pass-564!",
        })
        link = re.search(r"https?://[^\s]+/accounts/confirm-email/[^\s]+", mail.outbox[0].body).group()
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(link).status_code, 403)
        self.assertFalse(EmailAddress.objects.get(email="person@example.com").verified)
        invalid = reverse("account_confirm_email", args=["invalid"])
        self.assertContains(client.get(invalid), "نامعتبر")
        self.assertEqual(self.client.post(invalid).status_code, 404)

    def test_confirmation_does_not_offer_conflicting_email(self):
        from unittest.mock import patch
        from allauth.account.models import EmailConfirmationHMAC

        user = User.objects.create_user("person@example.com", "strong-pass-564!")
        address = EmailAddress.objects.create(user=user, email=user.email, primary=True)
        key = EmailConfirmationHMAC(address).key
        with patch.object(EmailAddress, "can_set_verified", return_value=False):
            response = self.client.get(reverse("account_confirm_email", args=[key]))
        self.assertContains(response, "قبلاً برای حساب دیگری تأیید شده است")
        self.assertNotContains(response, '<button type="submit">')

    def test_login_rejects_external_redirect(self):
        user = User.objects.create_user("person@example.com", "strong-pass-564!")
        EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)
        response = self.client.post(reverse("account_login") + "?next=https://evil.example/", {
            "login": user.email, "password": "strong-pass-564!",
        })
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("evil.example", response.url)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_password_reset_does_not_disclose_account(self):
        user = User.objects.create_user("person@example.com", "strong-pass-564!")
        EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)
        for email in (user.email, "missing@example.com"):
            response = self.client.post(reverse("account_reset_password"), {"email": email})
            self.assertRedirects(response, reverse("account_reset_password_done"))
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[0].to, [user.email])

    @override_settings(SOCIALACCOUNT_PROVIDERS={"google": {"APP": {
        "client_id": "test-client", "secret": "test-secret",
    }}})
    def test_google_callback_rejects_missing_state(self):
        response = self.client.get(reverse("google_callback"), {"code": "invalid"})
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertNotEqual(response.status_code, 500)
        self.assertFalse(User.objects.exists())

    @override_settings(SOCIALACCOUNT_PROVIDERS={"google": {"APP": {
        "client_id": "test-client", "secret": "test-secret",
    }}})
    def test_google_login_requires_post_and_csrf(self):
        from django.test import Client

        client = Client(enforce_csrf_checks=True)
        url = reverse("google_login")
        self.assertNotEqual(client.get(url).status_code, 302)
        self.assertEqual(client.post(url).status_code, 403)
        client.get(reverse("account_login"))
        response = client.post(url, {"csrfmiddlewaretoken": client.cookies["csrftoken"].value})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("https://accounts.google.com/"))
