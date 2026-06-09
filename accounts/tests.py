from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.core.files.uploadedfile import SimpleUploadedFile

User = get_user_model()

class AccountsAPITests(APITestCase):

    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="TestPassword123!",
            first_name="Test",
            last_name="User",
            bio="Original bio"
        )
        self.profile_url = reverse("auth-profile")
        self.reset_request_url = reverse("password-reset-request")
        self.reset_confirm_url = reverse("password-reset-confirm")

    def test_password_reset_flow_success(self):
        """Test full password reset flow with valid token and email."""
        # 1. Request password reset
        response = self.client.post(self.reset_request_url, {"email": "testuser@example.com"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["detail"], "If this email is registered, a reset link has been sent.")

        # Verify email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Reset your GoAttend password", mail.outbox[0].subject)
        
        # Extract reset URL from email body
        email_body = mail.outbox[0].body
        # Reset URL is in format: reset-password.html?uid=...&token=...
        self.assertIn("reset-password.html", email_body)
        
        # Parse uid and token from link
        import re
        match = re.search(r"uid=([a-zA-Z0-9_-]+)&token=([a-zA-Z0-9_-]+-[a-zA-Z0-9]+)", email_body)
        self.assertTrue(match)
        uid = match.group(1)
        token = match.group(2)

        # 2. Confirm password reset
        confirm_response = self.client.post(self.reset_confirm_url, {
            "uid": uid,
            "token": token,
            "new_password": "NewSecurePassword456!"
        })
        self.assertEqual(confirm_response.status_code, status.HTTP_200_OK)
        self.assertEqual(confirm_response.data["detail"], "Password has been reset successfully. You can now sign in.")

        # 3. Authenticate with new password
        login_url = reverse("auth-token-obtain")
        login_response = self.client.post(login_url, {
            "username": "testuser",
            "password": "NewSecurePassword456!"
        })
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", login_response.data)

    def test_password_reset_request_anti_enumeration(self):
        """Test that requesting reset for unregistered email still returns 200 and doesn't send email."""
        response = self.client.post(self.reset_request_url, {"email": "unknown@example.com"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["detail"], "If this email is registered, a reset link has been sent.")
        self.assertEqual(len(mail.outbox), 0)

    def test_password_reset_confirm_invalid_token(self):
        """Test password reset confirmation with invalid token/uid."""
        # Invalid uid
        response = self.client.post(self.reset_confirm_url, {
            "uid": "invaliduid",
            "token": "invalidtoken",
            "new_password": "NewSecurePassword456!"
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_profile_retrieve(self):
        """Test retrieving authenticated user's profile."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "testuser")
        self.assertEqual(response.data["first_name"], "Test")
        self.assertEqual(response.data["last_name"], "User")
        self.assertEqual(response.data["bio"], "Original bio")

    def test_profile_partial_update_success(self):
        """Test updating profile fields partially."""
        self.client.force_authenticate(user=self.user)
        
        # 1x1 GIF bytes for avatar
        gif_bytes = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00'
            b'\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
        )
        avatar_file = SimpleUploadedFile("avatar.gif", gif_bytes, content_type="image/gif")

        data = {
            "first_name": "UpdatedFirst",
            "last_name": "UpdatedLast",
            "bio": "Updated bio text",
            "avatar": avatar_file
        }

        response = self.client.patch(self.profile_url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["first_name"], "UpdatedFirst")
        self.assertEqual(response.data["last_name"], "UpdatedLast")
        self.assertEqual(response.data["bio"], "Updated bio text")
        self.assertIsNotNone(response.data["avatar"])
        
        # Clean up files created during test
        self.user.refresh_from_db()
        if self.user.avatar:
            self.user.avatar.delete(save=False)

    def test_profile_readonly_fields_are_ignored(self):
        """Test that read-only fields like role and email are ignored during profile updates."""
        self.client.force_authenticate(user=self.user)
        data = {
            "role": "organizer",
            "email": "hacker@example.com",
            "username": "hackeruser",
            "bio": "Keep this updated bio"
        }
        response = self.client.patch(self.profile_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["role"], "regular")
        self.assertEqual(response.data["email"], "testuser@example.com")
        self.assertEqual(response.data["username"], "testuser")
        self.assertEqual(response.data["bio"], "Keep this updated bio")

        # Verify in DB
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, "regular")
        self.assertEqual(self.user.email, "testuser@example.com")
        self.assertEqual(self.user.username, "testuser")
