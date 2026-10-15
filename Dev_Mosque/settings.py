from pathlib import Path
import os

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


SECRET_KEY = os.getenv("SECRET_KEY", "development-only-secret-key")
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    "nifrash.pythonanywhere.com",
]

CSRF_TRUSTED_ORIGINS = [
    "https://nifrash.pythonanywhere.com",
]


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "accounts",
    "locations",
    "mosques",
    "support_requests",
    "platform_control",
    "core",
    "dashboard",
    "ui_system",
]


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


ROOT_URLCONF = "Dev_Mosque.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "support_requests.context_processors.platform_notifications",
            ],
        },
    },
]

WSGI_APPLICATION = "Dev_Mosque.wsgi.application"


# Production: PythonAnywhere MySQL. Local development falls back to SQLite
# when MYSQL_DATABASE is not supplied.
if os.getenv("MYSQL_DATABASE"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": os.getenv("MYSQL_DATABASE"),
            "USER": os.getenv("MYSQL_USER"),
            "PASSWORD": os.getenv("MYSQL_PASSWORD"),
            "HOST": os.getenv("MYSQL_HOST"),
            "PORT": os.getenv("MYSQL_PORT", "3306"),
            "OPTIONS": {
                "charset": "utf8mb4",
            },
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "accounts.backends.UsernameOrEmailBackend",
]

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "dashboard:home"


LANGUAGE_CODE = "en"
LANGUAGES = [
    ("en", "English"),
    ("ta", "தமிழ்"),
    ("ar", "العربية"),
]
TIME_ZONE = "Asia/Colombo"
USE_I18N = True
USE_TZ = True
LOCALE_PATHS = [BASE_DIR / "locale"]


STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL",
    "Sri Lanka Mosque Platform <noreply@mosques.lk>",
)

# Phase 6 compatibility / development fallback.
SUPPORT_SMS_BACKEND = os.getenv(
    "SUPPORT_SMS_BACKEND",
    "support_requests.sms_backends.ConsoleSMSBackend",
)

# Phase 9 platform notifications.
NOTIFICATION_SMS_BACKEND = os.getenv(
    "NOTIFICATION_SMS_BACKEND",
    SUPPORT_SMS_BACKEND,
)

# Phase 10 SMS OTP verification.
OTP_SMS_BACKEND = os.getenv(
    "OTP_SMS_BACKEND",
    NOTIFICATION_SMS_BACKEND,
)
OTP_CODE_LENGTH = int(os.getenv("OTP_CODE_LENGTH", "6"))
OTP_EXPIRY_SECONDS = int(os.getenv("OTP_EXPIRY_SECONDS", "300"))
OTP_RESEND_COOLDOWN_SECONDS = int(os.getenv("OTP_RESEND_COOLDOWN_SECONDS", "60"))
OTP_MAX_ATTEMPTS = int(os.getenv("OTP_MAX_ATTEMPTS", "5"))
OTP_MAX_SENDS_PER_HOUR = int(os.getenv("OTP_MAX_SENDS_PER_HOUR", "5"))
SMS_DEFAULT_COUNTRY_CODE = os.getenv("SMS_DEFAULT_COUNTRY_CODE", "+94")


LANGUAGE_COOKIE_NAME = "mosque_language"
LANGUAGE_COOKIE_AGE = 60 * 60 * 24 * 365
LANGUAGE_COOKIE_SAMESITE = "Lax"

CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "info@mosques.lk")


# ============================================================
# EMAIL (Gmail SMTP)
# ============================================================
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() == "true"
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "False").lower() == "true"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", "20"))

DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL",
    EMAIL_HOST_USER or "noreply@mosques.lk",
)

# ============================================================
# SMS - Text.lk
# ============================================================
TEXTLK_API_URL = os.getenv(
    "TEXTLK_API_URL",
    "https://app.text.lk/api/v3/sms/send",
)
TEXTLK_API_TOKEN = os.getenv("TEXTLK_API_TOKEN", "")
TEXTLK_SENDER_ID = os.getenv("TEXTLK_SENDER_ID", "")
TEXTLK_DLT_TEMPLATE_ID = os.getenv("TEXTLK_DLT_TEMPLATE_ID", "")
TEXTLK_TIMEOUT_SECONDS = int(os.getenv("TEXTLK_TIMEOUT_SECONDS", "20"))

SUPPORT_SMS_BACKEND = os.getenv(
    "SUPPORT_SMS_BACKEND",
    "support_requests.sms_backends.ConsoleSMSBackend",
)
NOTIFICATION_SMS_BACKEND = os.getenv(
    "NOTIFICATION_SMS_BACKEND",
    SUPPORT_SMS_BACKEND,
)
OTP_SMS_BACKEND = os.getenv(
    "OTP_SMS_BACKEND",
    NOTIFICATION_SMS_BACKEND,
)

OTP_CODE_LENGTH = int(os.getenv("OTP_CODE_LENGTH", "6"))
OTP_EXPIRY_SECONDS = int(os.getenv("OTP_EXPIRY_SECONDS", "300"))
OTP_RESEND_COOLDOWN_SECONDS = int(
    os.getenv("OTP_RESEND_COOLDOWN_SECONDS", "60")
)
OTP_MAX_ATTEMPTS = int(os.getenv("OTP_MAX_ATTEMPTS", "5"))
OTP_MAX_SENDS_PER_HOUR = int(
    os.getenv("OTP_MAX_SENDS_PER_HOUR", "5")
)
SMS_DEFAULT_COUNTRY_CODE = os.getenv(
    "SMS_DEFAULT_COUNTRY_CODE",
    "+94",
)
