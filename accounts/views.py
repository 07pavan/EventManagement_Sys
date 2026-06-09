"""
accounts/views.py

Auth and user-profile API views.

Rate limiting strategy:
  All endpoints are protected by DRF's AnonRateThrottle + UserRateThrottle
  configured globally in settings.REST_FRAMEWORK. We do NOT use
  django_ratelimit here — two separate rate-limiting systems on the same
  view conflict and produce inconsistent behavior (one may block while
  the other passes). DRF throttling is the single source of truth.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.core.mail import send_mail
from django.conf import settings
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import (
    CustomTokenObtainPairSerializer,
    UserRegistrationSerializer,
    UserProfileSerializer,
)

User = get_user_model()


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    POST /api/auth/token/

    Returns an access + refresh JWT pair enriched with role & username.

    Rate limiting: handled globally by DRF AnonRateThrottle (60/min).
    The previous django_ratelimit decorator has been removed to avoid
    two conflicting rate-limit systems on the same endpoint.

    Responses:
      200 — { access, refresh }
      401 — bad credentials
      429 — rate limit exceeded (DRF throttle)
    """
    serializer_class = CustomTokenObtainPairSerializer


class RegisterView(generics.CreateAPIView):
    """
    POST /api/auth/register/

    Open endpoint — no authentication required.
    Creates a new regular user account. Role is always 'regular'
    regardless of what the client sends.

    Rate limiting: handled globally by DRF AnonRateThrottle (60/min).
    """
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = UserRegistrationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                "message": "Account created successfully.",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": user.role,   # Always "regular" — confirmed by serializer
                },
            },
            status=status.HTTP_201_CREATED,
        )


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/auth/profile/  — retrieve own profile
    PATCH /api/auth/profile/  — partial update own profile

    WHY PATCH only (not PUT):
    PUT requires ALL fields to be sent — if a client omits `avatar`,
    the avatar gets wiped. PATCH allows sending only the fields being
    changed. We enforce `partial=True` on PATCH calls automatically via
    `http_method_names` limiting and DRF's partial update logic.

    Writable: first_name, last_name, bio, avatar
    Read-only: id, username, role, email, date_joined
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    # Disable PUT — profile updates must use PATCH (partial update only)
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return self.request.user

    def partial_update(self, request, *args, **kwargs):
        """Force partial=True so omitted fields are not wiped."""
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)


class LogoutView(generics.GenericAPIView):
    """
    POST /api/auth/logout/

    Accepts a refresh token in the request body and blacklists it,
    invalidating the session server-side. The client must also
    clear its local token storage (localStorage/sessionStorage).

    Body: { "refresh": "<refresh-token>" }
    Auth: Bearer token required.

    WHY blacklist on logout:
    JWTs are stateless — there is no server session to destroy.
    The only way to truly invalidate a JWT before expiry is to
    track it in a blacklist. SimpleJWT's token_blacklist app
    provides this. Without blacklisting, a logged-out user's
    stolen refresh token remains valid for 7 days.

    Responses:
      205 — token blacklisted successfully
      400 — missing or invalid/already-blacklisted refresh token
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from rest_framework_simplejwt.tokens import RefreshToken
        from rest_framework_simplejwt.exceptions import TokenError

        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"detail": "Refresh token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(
                {"detail": "Successfully logged out."},
                status=status.HTTP_205_RESET_CONTENT,
            )
        except TokenError:
            # Token already blacklisted or malformed — treat as logout success
            # to avoid leaking information about token state
            return Response(
                {"detail": "Token is invalid or already blacklisted."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class IsOrganizerCheckView(generics.GenericAPIView):
    """
    GET /api/auth/is-organizer/

    Lightweight gate check used by the scanner page on load.
    Confirms the authenticated user holds the organizer role.
    Auth: Bearer token required.

    Responses:
      200 — { "is_organizer": true,  "username": "...", "role": "organizer" }
      403 — { "is_organizer": false, "detail": "Access denied..." }
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not request.user.is_organizer:
            return Response(
                {
                    "is_organizer": False,
                    "detail": "Access denied. Organizer role required.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(
            {
                "is_organizer": True,
                "username": request.user.username,
                "role": request.user.role,
                "email": request.user.email,
            },
            status=status.HTTP_200_OK,
        )


class PasswordResetRequestView(generics.GenericAPIView):
    """
    POST /api/auth/password-reset/

    Accepts: { "email": "<user-email>" }
    Auth:    None required — open endpoint.

    Looks up the user by email, generates a Django password-reset token
    (uidb64 + token), and sends a link to the user's email address.

    SECURITY — Anti-enumeration:
    Always returns HTTP 200 regardless of whether the email is registered.
    This prevents attackers from probing which emails exist in the system.

    TOKEN SECURITY:
    Uses Django's default_token_generator (PasswordResetTokenGenerator).
      - Time-limited: expires after PASSWORD_RESET_TIMEOUT seconds (default 3 days).
      - Single-use: the token is invalidated as soon as the password changes.
      - Cryptographically tied to the user's password hash, pk, and last_login.

    Responses:
      200 — { "detail": "If this email is registered, a reset link has been sent." }
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip().lower()

        # Attempt to find the user — but silently continue if not found
        # to preserve anti-enumeration protection.
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Do NOT reveal that the email does not exist
            return Response(
                {"detail": "If this email is registered, a reset link has been sent."},
                status=status.HTTP_200_OK,
            )

        # Generate uidb64 + token
        uid   = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        # Build the reset URL pointing to the frontend reset page
        frontend_url = getattr(settings, "FRONTEND_URL", "http://127.0.0.1:5500/frontend")
        reset_url    = f"{frontend_url}/reset-password.html?uid={uid}&token={token}"

        # Send the email
        subject = "Reset your GoAttend password"
        message = (
            f"Hi {user.username},\n\n"
            f"We received a request to reset your password for your GoAttend account.\n\n"
            f"Click the link below to choose a new password:\n\n"
            f"  {reset_url}\n\n"
            f"This link is valid for 3 days and can only be used once.\n\n"
            f"If you did not request a password reset, you can safely ignore this email.\n\n"
            f"— The GoAttend Team"
        )
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=True,   # Don't crash the view if mail server is down
        )

        return Response(
            {"detail": "If this email is registered, a reset link has been sent."},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(generics.GenericAPIView):
    """
    POST /api/auth/password-reset/confirm/

    Accepts: { "uid": "<uidb64>", "token": "<token>", "new_password": "<password>" }
    Auth:    None required — open endpoint (protected by token validity).

    Validates the uidb64 + token pair generated by PasswordResetRequestView,
    runs Django's AUTH_PASSWORD_VALIDATORS on the new password,
    and saves the new hashed password.

    Responses:
      200 — { "detail": "Password has been reset successfully." }
      400 — { "detail": "<error message>" }
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        uid          = request.data.get("uid", "").strip()
        token        = request.data.get("token", "").strip()
        new_password = request.data.get("new_password", "").strip()

        # Validate required fields
        if not uid or not token or not new_password:
            return Response(
                {"detail": "uid, token, and new_password are all required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Decode uidb64 → user pk
        try:
            user_pk = force_str(urlsafe_base64_decode(uid))
            user    = User.objects.get(pk=user_pk)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response(
                {"detail": "Invalid or expired reset link."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate the token (time-limited, single-use)
        if not default_token_generator.check_token(user, token):
            return Response(
                {"detail": "Invalid or expired reset link. Please request a new one."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Run AUTH_PASSWORD_VALIDATORS
        try:
            validate_password(new_password, user=user)
        except DjangoValidationError as exc:
            return Response(
                {"detail": " ".join(exc.messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Save the new hashed password
        # set_password() handles hashing; calling save() persists it.
        # This also invalidates the token (it is tied to the password hash).
        user.set_password(new_password)
        user.save(update_fields=["password"])

        return Response(
            {"detail": "Password has been reset successfully. You can now sign in."},
            status=status.HTTP_200_OK,
        )
