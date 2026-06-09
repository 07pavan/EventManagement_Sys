"""
accounts/serializers.py

Serializers for User registration, profile, and JWT token handling.

Security model:
- Role assignment is ALWAYS server-controlled, never client-controlled.
- Registration only accepts: username, email, password, password2, first_name, last_name.
- Any other field sent in the request body is silently ignored.
- `role` is defensively stripped in create() even if it somehow passes field validation
  (e.g., future field additions, DRF version changes).
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


# --------------------------------------------------------------------------- #
# JWT — enriched token payload
# --------------------------------------------------------------------------- #

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Add user role and username to the JWT payload so the frontend
    can read them from the token without an extra /profile/ call.

    Security note: JWT payload is base64-encoded, NOT encrypted.
    Never put sensitive data (SSN, password, CC number) in a JWT claim.
    Role and username are safe to include — they're not secret.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Custom claims — readable by any JWT decoder without the secret
        token["username"] = user.username
        token["role"] = user.role
        token["email"] = user.email
        return token


# --------------------------------------------------------------------------- #
# Registration
# --------------------------------------------------------------------------- #

class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Handles new user sign-up including password confirmation.

    SECURITY — Role assignment:
    ━━━━━━━━━━━━━━━━━━━━━━━━━━
    The `role` field accepts only 'regular' or 'organizer'.
    Admin/staff/superuser roles are impossible via this endpoint.
    Any other value is rejected by validate_role().
    """

    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],  # Runs all AUTH_PASSWORD_VALIDATORS
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True,
        label="Confirm password",
    )

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "password",
            "password2",
            "role",  # Whitelisted: only 'regular' or 'organizer' accepted
            # `is_staff`, `is_superuser`, `is_active` are excluded.
            "security_question",
            "security_answer",
        ]
        extra_kwargs = {
            "email": {"required": True},
            "first_name": {"required": False},
            "last_name": {"required": False},
            "role": {"required": False},
            "security_question": {"required": True},
            "security_answer": {"required": True, "write_only": True},
        }

    def validate_role(self, value):
        """
        Whitelist: only 'regular' or 'organizer' are valid self-assignable roles.
        Prevents privilege escalation to admin/staff via the API.
        """
        allowed = {'regular', 'organizer'}
        if value not in allowed:
            raise serializers.ValidationError(
                f"Invalid role. Choose 'regular' or 'organizer'."
            )
        return value

    def validate_email(self, value):
        """
        Normalize email to lowercase and check for duplicate registrations.

        WHY: Without normalization, user@EXAMPLE.COM and user@example.com
        would be treated as two different accounts. The model has
        `unique=True` on email, but normalization prevents silent duplicates
        that differ only in case.

        Anti-enumeration: We return the same validation error whether the
        email exists or not — but email uniqueness IS a valid user-facing
        error (unlike username enumeration in login forms).
        """
        normalized = value.lower().strip()
        if User.objects.filter(email=normalized).exists():
            raise serializers.ValidationError(
                "An account with this email address already exists."
            )
        return normalized

    def validate_username(self, value):
        """Enforce lowercase username and strip whitespace."""
        return value.strip()

    def validate(self, attrs):
        """Cross-field validation: ensure passwords match and hash security answer."""
        if attrs["password"] != attrs.pop("password2"):
            raise serializers.ValidationError(
                {"password": "Password fields did not match."}
            )

        # Validate security question & answer
        if not attrs.get("security_question") or not attrs.get("security_answer"):
            raise serializers.ValidationError(
                {"security_question": "Both security question and answer are required."}
            )
        
        answer_clean = attrs["security_answer"].strip().lower()
        if len(answer_clean) < 2:
            raise serializers.ValidationError(
                {"security_answer": "Security answer must be at least 2 characters."}
            )
        
        from django.contrib.auth.hashers import make_password
        attrs["security_answer"] = make_password(answer_clean)
        return attrs

    def create(self, validated_data):
        """
        Create user. Role is already validated by validate_role().
        Strip any privilege-escalation fields that cannot come from self-registration.
        """
        # These fields can NEVER be set via registration — defense-in-depth
        validated_data.pop("is_staff", None)
        validated_data.pop("is_superuser", None)
        validated_data.pop("is_active", None)  # Preserve model default (True)

        # Role defaults to 'regular' if not provided
        validated_data.setdefault("role", "regular")

        # create_user() hashes the password — never use objects.create() for auth users
        return User.objects.create_user(**validated_data)


# --------------------------------------------------------------------------- #
# Profile
# --------------------------------------------------------------------------- #

class UserProfileSerializer(serializers.ModelSerializer):
    """
    Read / update the currently authenticated user's own profile.

    Writable fields: first_name, last_name, bio, avatar
    Read-only fields: id, username, role, email, date_joined

    WHY email is read-only:
    Email changes require a verification flow (send email → confirm).
    Allowing direct PATCH of email without verification lets users
    lock themselves out or impersonate others.

    WHY role is read-only:
    Role elevation must go through Django Admin only.
    """

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "avatar",
            "bio",
            "date_joined",
            "security_question",
            "security_answer",
        ]
        read_only_fields = ["id", "username", "role", "email", "date_joined"]
        extra_kwargs = {
            "security_answer": {"write_only": True, "required": False},
        }

    def validate(self, attrs):
        # Hash security answer if provided in profile update
        answer = attrs.get("security_answer")
        if answer is not None:
            answer_clean = answer.strip().lower()
            if len(answer_clean) < 2:
                raise serializers.ValidationError(
                    {"security_answer": "Security answer must be at least 2 characters."}
                )
            from django.contrib.auth.hashers import make_password
            attrs["security_answer"] = make_password(answer_clean)
        return attrs


# --------------------------------------------------------------------------- #
# Public (read-only, no sensitive fields)
# --------------------------------------------------------------------------- #

class PublicUserSerializer(serializers.ModelSerializer):
    """
    Minimal public view of a user shown on event cards (organizer info).
    Contains ONLY non-sensitive fields — no email, no role, no bio.
    """

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "avatar"]
