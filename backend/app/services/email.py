"""Sending email (password reset links) through Brevo's HTTP API (free tier).

HTTP rather than SMTP: Render's free plan is believed to block outgoing SMTP ports. When
BREVO_API_KEY isn't set, emails aren't sent: in development the message goes to the log instead
(so the flow can be tested locally), in production the features that need email are hidden.
"""
import logging

import httpx

from app import config

log = logging.getLogger("tandurust.email")
BREVO_URL = "https://api.brevo.com/v3/smtp/email"


def enabled() -> bool:
    """Can we deliver emails (or, in development, show them in the log)?"""
    if config.BREVO_API_KEY and config.EMAIL_FROM and config.PUBLIC_APP_URL:
        return True
    return not config.COOKIE_SECURE and bool(config.PUBLIC_APP_URL)


def send(to: str, subject: str, text: str) -> None:
    """Send a plain-text email. Runs after the response (background task); failures are logged."""
    if not (config.BREVO_API_KEY and config.EMAIL_FROM):
        log.info("Email not sent (no BREVO_API_KEY). To %s: %s\n%s", to, subject, text)
        return
    try:
        r = httpx.post(BREVO_URL, timeout=15, headers={"api-key": config.BREVO_API_KEY, "accept": "application/json"},
                       json={"sender": {"name": config.APP_NAME, "email": config.EMAIL_FROM},
                             "to": [{"email": to}], "subject": subject, "textContent": text})
        if r.status_code >= 300:
            log.error("Brevo refused the email (%s): %s", r.status_code, r.text[:300])
    except httpx.HTTPError as e:
        log.error("Couldn't reach Brevo: %s", e)
