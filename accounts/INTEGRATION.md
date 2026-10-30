# ادغام حساب‌ها

این اپ از `django-allauth[socialaccount]>=65.3,<66` استفاده می‌کند؛ وابستگی را به `requirements.txt` اضافه و نصب کنید. تنظیمات زیر باید در تنظیمات اصلی اعمال شوند؛ `accounts.test_settings` فقط برای آزمون است.

```python
INSTALLED_APPS += [
    "allauth", "allauth.account", "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
]
MIDDLEWARE += ["allauth.account.middleware.AccountMiddleware"]
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 3
SOCIALACCOUNT_EMAIL_AUTHENTICATION = False
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = False
SOCIALACCOUNT_LOGIN_ON_GET = False
SOCIALACCOUNT_PROVIDERS = {
    "google": {"APP": {
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "secret": os.environ["GOOGLE_CLIENT_SECRET"],
    }},
}
```

- در URL اصلی `path("accounts/", include("accounts.urls"))` را اضافه کنید؛ فضای نام به URLهای allauth ندهید. `base.html` باید بلوک `content` داشته باشد.
- migrationهای allauth را اعمال کنید. اعتبارنامه Google OAuth را از متغیر محیطی بگیرید؛ callback دقیق `https://DOMAIN/accounts/google/login/callback/` را در Google ثبت کنید. HTTPS، تنظیمات امن session/CSRF، `SECRET_KEY` پایدار، `ALLOWED_HOSTS` و ایمیل خروجی واقعی ضروری‌اند. برای تولید لینک‌های معتبر، دامنه میزبان معتبر و تنظیمات proxy مورد اعتماد را به‌درستی پیکربندی کنید.
- migration `accounts.0002` در MySQL برای ایمیل تأییدشده و ایمیل اصلی محدودیت یکتایی در پایگاه داده می‌سازد؛ هشدارهای `models.W036` مربوط به محدودیت‌های شرطی مدل allauth همچنان نمایش داده می‌شوند. پیش از استقرار از پایگاه داده نسخه پشتیبان بگیرید و رکوردهای تکراری تأییدشده بر اساس ایمیل و رکوردهای اصلی تکراری بر اساس کاربر را بررسی کنید. migration در صورت وجود تکرار شکست می‌خورد؛ مالکیت ایمیل را پیش از اصلاح دستی بررسی کنید. بازگردانی migration این حفاظت‌ها را حذف می‌کند. پس از ارتقای allauth، نام جدول، فیلدها و محدودیت‌ها را دوباره بررسی کنید.
- اتصال خودکار حساب Google به حساب موجود با ایمیل یکسان خاموش است؛ اتصال نیازمند ورود به حساب موجود و جریان اتصال صریح است. حساب‌های موجود پیش از این تغییر به رکورد تأیید allauth نیاز دارند؛ بدون بررسی مالکیت ایمیل، آنها را تأییدشده علامت نزنید. حساب‌های مدیر همچنان از مسیر admin و backend استاندارد قابل ورودند؛ دسترسی admin را جداگانه محدود کنید.
- محدودیت‌های پیش‌فرض allauth برای ورود، خطای ورود، ثبت‌نام و بازیابی گذرواژه فعال‌اند؛ برای چند پردازه یا چند سرور cache مشترک با عملیات اتمی و تنظیم درست IP کلاینت در proxy لازم است. cache پیش‌فرض محلی برای محدودسازی سراسری کافی نیست. مسیر admin جداگانه محدودسازی لازم دارد. مقادیر `ACCOUNT_RATE_LIMITS` و سیاست لبه شبکه را بر اساس محیط بازبینی کنید.
- هنگام نبود اعتبارنامه، دکمه Google نمایش داده نمی‌شود؛ در صورت پیکربندی، از تعریف تکراری برنامه Google در تنظیمات و پایگاه داده خودداری کنید.
- آزمون MySQL: `python manage.py test accounts --settings=accounts.test_settings`. کاربر پایگاه داده باید مجوز ساخت پایگاه داده آزمون داشته باشد.
