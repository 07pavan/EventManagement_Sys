import logging
import requests
from django.core.mail.backends.base import BaseEmailBackend
from django.conf import settings

logger = logging.getLogger(__name__)

class ResendAPIBackend(BaseEmailBackend):
    """
    Custom Django email backend that sends emails via Resend's HTTP API (port 443 HTTPS).
    This bypasses Render's port 587/465 SMTP blocking on their Free tier.
    """

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        api_key = getattr(settings, "EMAIL_HOST_PASSWORD", "")
        if not api_key:
            logger.error("Resend API key (EMAIL_HOST_PASSWORD) is not configured.")
            return 0

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        sent_count = 0
        for message in email_messages:
            payload = {
                "from": message.from_email or settings.DEFAULT_FROM_EMAIL,
                "to": message.to,
                "subject": message.subject,
            }

            # Resend API supports html or text fields
            if getattr(message, "alternatives", None):
                # If there's an HTML alternative (e.g. EmailMultiAlternatives)
                for content, mimetype in message.alternatives:
                    if mimetype == "text/html":
                        payload["html"] = content
                        break

            # Fallback to plain text if HTML not found or not present
            if "html" not in payload:
                payload["text"] = message.body

            try:
                res = requests.post(
                    "https://api.resend.com/emails",
                    json=payload,
                    headers=headers,
                    timeout=10,
                )
                if res.status_code in [200, 201]:
                    sent_count += 1
                else:
                    logger.error(
                        f"Resend API returned status code {res.status_code}: {res.text}"
                    )
            except Exception as e:
                logger.error(f"Failed to connect to Resend API: {e}", exc_info=True)

        return sent_count
