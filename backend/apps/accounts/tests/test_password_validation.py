from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from apps.organizations.models import Organization

User = get_user_model()


class PasswordValidationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = "/api/v1/auth/register/"
        self.valid_payload = {
            "organization_name": "Test Org",
            "organization_slug": "test-org",
            "email": "test@example.com",
            "username": "testuser",
        }

    def test_registration_rejects_weak_password(self):
        """
        Verify that registration rejects a common/weak password.
        """
        payload = self.valid_payload.copy()
        payload["password"] = "password123"  # Common password

        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

        # Confirm no user or organization was created
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(Organization.objects.count(), 0)

    def test_registration_rejects_short_password(self):
        """
        Verify that registration rejects a short password.
        """
        payload = self.valid_payload.copy()
        payload["password"] = "12345"  # Short password

        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_registration_accepts_valid_password(self):
        """
        Verify that registration accepts a strong, valid password.
        """
        payload = self.valid_payload.copy()
        payload["password"] = "Str0ng!P@ssw0rd2026"

        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Confirm user and organization were created
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(Organization.objects.count(), 1)

    def test_registration_rejects_username_similar_password(self):
        """
        Verify that registration rejects a password that is too similar to the username.
        """
        payload = self.valid_payload.copy()
        # Payload username is 'testuser'
        # Let's use a password that is highly similar to the username, but has enough characters/symbols
        # to avoid min_length (8) and common password checks.
        payload["password"] = "testuser!@#"

        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)
