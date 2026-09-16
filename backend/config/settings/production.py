from django.core.exceptions import ImproperlyConfigured
from .base import *


DEBUG = False

if not SECRET_KEY or SECRET_KEY == "development-secret-key":
    raise ImproperlyConfigured("SECRET_KEY must be explicitly configured in production.")

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
JWT_REFRESH_COOKIE_SECURE = True
