import os
import importlib
from unittest import mock
import pytest
from django.core.exceptions import ImproperlyConfigured

def test_base_settings_parsing():
    """Verify that base settings parse comma-separated env variables properly."""
    env_vars = {
        "ALLOWED_HOSTS": "api.example.com, admin.example.com ",
        "CORS_ALLOWED_ORIGINS": "https://app.example.com, https://example.com"
    }
    with mock.patch.dict(os.environ, env_vars):
        import config.settings.base as base_settings
        importlib.reload(base_settings)

        assert "api.example.com" in base_settings.ALLOWED_HOSTS
        assert "admin.example.com" in base_settings.ALLOWED_HOSTS
        assert "*" not in base_settings.ALLOWED_HOSTS
        assert len(base_settings.ALLOWED_HOSTS) == 2

        assert "https://app.example.com" in base_settings.CORS_ALLOWED_ORIGINS
        assert "https://example.com" in base_settings.CORS_ALLOWED_ORIGINS
        assert len(base_settings.CORS_ALLOWED_ORIGINS) == 2

def test_development_settings():
    """Verify development settings always allow localhost."""
    env_vars = {
        "ALLOWED_HOSTS": "api.local",
        "CORS_ALLOWED_ORIGINS": "http://app.local"
    }
    with mock.patch.dict(os.environ, env_vars):
        import config.settings.base as base_settings
        importlib.reload(base_settings)
        import config.settings.development as dev_settings
        importlib.reload(dev_settings)

        # Should contain both environment additions and localhost defaults
        assert "localhost" in dev_settings.ALLOWED_HOSTS
        assert "127.0.0.1" in dev_settings.ALLOWED_HOSTS
        assert "api.local" in dev_settings.ALLOWED_HOSTS

        assert "http://localhost:3000" in dev_settings.CORS_ALLOWED_ORIGINS
        assert "http://app.local" in dev_settings.CORS_ALLOWED_ORIGINS

def test_production_settings_safe_fallback():
    """Verify production settings fail safely (empty list) rather than allowing wildcard."""
    # Ensure environment has no HOST/CORS vars but has a valid SECRET_KEY
    with mock.patch.dict(os.environ, {"SECRET_KEY": "valid-production-secret-key-12345"}):
        if "ALLOWED_HOSTS" in os.environ:
            del os.environ["ALLOWED_HOSTS"]
        if "CORS_ALLOWED_ORIGINS" in os.environ:
            del os.environ["CORS_ALLOWED_ORIGINS"]

        import config.settings.base as base_settings
        importlib.reload(base_settings)
        import config.settings.production as prod_settings
        importlib.reload(prod_settings)

        assert prod_settings.ALLOWED_HOSTS == []
        assert prod_settings.CORS_ALLOWED_ORIGINS == []
        assert "*" not in prod_settings.ALLOWED_HOSTS
        assert prod_settings.DEBUG is False

def test_production_secret_key_fails_fast():
    """Verify production settings raise ImproperlyConfigured if SECRET_KEY is default or empty."""
    with mock.patch("dotenv.load_dotenv"):
        with mock.patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ImproperlyConfigured, match="SECRET_KEY must be explicitly configured in production"):
                import config.settings.base as base_settings
                importlib.reload(base_settings)
                import config.settings.production as prod_settings
                importlib.reload(prod_settings)

        with mock.patch.dict(os.environ, {"SECRET_KEY": "development-secret-key"}):
            with pytest.raises(ImproperlyConfigured, match="SECRET_KEY must be explicitly configured in production"):
                import config.settings.base as base_settings
                importlib.reload(base_settings)
                import config.settings.production as prod_settings
                importlib.reload(prod_settings)
