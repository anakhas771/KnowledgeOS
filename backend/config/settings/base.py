from pathlib import Path
import os
from dotenv import load_dotenv

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv(BASE_DIR / ".env")
# Security
SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "development-secret-key"
)


DEBUG = True


ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
]


# Applications

INSTALLED_APPS = [

    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",


    # Third party
    "rest_framework",
    "corsheaders",


    # Local apps
]


# Middleware

MIDDLEWARE = [

    "corsheaders.middleware.CorsMiddleware",

    "django.middleware.security.SecurityMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",

    "django.middleware.common.CommonMiddleware",

    "django.middleware.csrf.CsrfViewMiddleware",

    "django.contrib.auth.middleware.AuthenticationMiddleware",

    "django.contrib.messages.middleware.MessageMiddleware",

    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


ROOT_URLCONF = "config.urls"


# Templates

TEMPLATES = [

    {
        "BACKEND":
        "django.template.backends.django.DjangoTemplates",

        "DIRS": [],

        "APP_DIRS": True,

        "OPTIONS":
        {
            "context_processors":
            [

                "django.template.context_processors.request",

                "django.contrib.auth.context_processors.auth",

                "django.contrib.messages.context_processors.messages",

            ],
        },
    },
]


WSGI_APPLICATION = "config.wsgi.application"

ASGI_APPLICATION = "config.asgi.application"


# Database

DATABASES = {

    "default": {

        "ENGINE":
        "django.db.backends.postgresql",

        "NAME":
        os.getenv("POSTGRES_DB"),

        "USER":
        os.getenv("POSTGRES_USER"),

        "PASSWORD":
        os.getenv("POSTGRES_PASSWORD"),

        "HOST":
        os.getenv("POSTGRES_HOST"),

        "PORT":
        os.getenv("POSTGRES_PORT"),

    }

}


# Password validation

AUTH_PASSWORD_VALIDATORS = []


# Internationalization

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Asia/Kolkata"

USE_I18N = True

USE_TZ = True



# Static files

STATIC_URL = "static/"


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"



# Django REST Framework

REST_FRAMEWORK = {


    "DEFAULT_AUTHENTICATION_CLASSES":

    (

        "rest_framework_simplejwt.authentication.JWTAuthentication",

    ),


}