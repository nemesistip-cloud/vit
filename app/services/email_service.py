# app/services/email_service.py
"""Styled HTML email delivery for all VIT notification types.

Supports:
  - SMTP (SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASS / SMTP_FROM)
  - Resend.com API (RESEND_API_KEY) — takes priority when set
Falls back to console log in dev when neither is configured.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_FROM = os.getenv("SMTP_FROM", "VIT Network <noreply@vit.network>")
_APP_NAME = "VIT Sports Intelligence"
_PRIMARY = "#00e5ff"   # brand cyan


# ── HTML template ──────────────────────────────────────────────────────────────

def _html_wrapper(title: str, body_html: str, footer: str = "") -> str:
    """Wrap content in a clean VIT-branded email template."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{title}</title>
</head>
<body style="margin:0;padding:0;background:#0a0a0f;font-family:'Segoe UI',Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0a0a0f;padding:32px 16px;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0"
             style="background:#111118;border-radius:12px;border:1px solid #1e1e2e;overflow:hidden;max-width:600px;">

        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#0d1f2d,#0a1628);padding:28px 32px;text-align:center;border-bottom:1px solid #1e1e2e;">
            <div style="font-size:22px;font-weight:700;color:{_PRIMARY};letter-spacing:1px;font-family:monospace;">
              VIT_OS
            </div>
            <div style="font-size:11px;color:#555;margin-top:4px;letter-spacing:2px;text-transform:uppercase;">
              Sports Intelligence Network
            </div>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding:32px;">
            <h2 style="margin:0 0 16px;color:#e8e8f0;font-size:18px;font-weight:600;">{title}</h2>
            <div style="color:#a0a0b8;font-size:14px;line-height:1.7;">
              {body_html}
            </div>
          </td>
        </tr>

        <!-- CTA divider -->
        <tr>
          <td style="padding:0 32px 24px;">
            <div style="border-top:1px solid #1e1e2e;"></div>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="padding:0 32px 28px;text-align:center;">
            <div style="font-size:11px;color:#444;line-height:1.6;">
              {footer or f"You&rsquo;re receiving this because you have an account on {_APP_NAME}."}
              <br/>To manage your notification preferences, visit your account settings.
            </div>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


# ── Per-type templates ──────────────────────────────────────────────────────────

def _build_email_html(ntype: str, title: str, body: str, username: str = "") -> tuple[str, str]:
    """Return (subject, html) for the given notification type."""
    greeting = f"Hi {username}," if username else "Hello,"
    type_icons = {
        "prediction_alert":   "🎯",
        "match_result":       "⚽",
        "wallet_activity":    "💰",
        "validator_reward":   "🏆",
        "subscription_expiry": "⚠️",
        "validator_status":   "🛡️",
        "system":             "🔔",
    }
    icon = type_icons.get(ntype, "🔔")

    body_html = f"""
    <p style="margin:0 0 12px;color:#c0c0d8;">{greeting}</p>
    <div style="background:#0d1117;border-left:3px solid {_PRIMARY};border-radius:6px;
                padding:16px 20px;margin:16px 0;">
      <div style="font-size:22px;margin-bottom:8px;">{icon}</div>
      <div style="color:#e0e0f0;font-size:15px;font-weight:600;margin-bottom:8px;">{title}</div>
      <div style="color:#a0a0b8;font-size:14px;line-height:1.6;">{body}</div>
    </div>
    <p style="margin:16px 0 0;color:#666;font-size:13px;">
      Log in to your VIT dashboard to see full details and manage your predictions.
    </p>
    """

    subject = f"{icon} {title}"
    html = _html_wrapper(title, body_html)
    return subject, html


# ── Transport ──────────────────────────────────────────────────────────────────

async def _send_via_resend(to: str, subject: str, html: str) -> bool:
    """Send email via Resend.com API."""
    api_key = os.getenv("RESEND_API_KEY", "")
    if not api_key:
        return False
    try:
        import httpx
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"from": _FROM, "to": [to], "subject": subject, "html": html},
            )
            if r.status_code in (200, 201):
                logger.info(f"Email sent via Resend: to={to} subject={subject[:50]}")
                return True
            logger.warning(f"Resend error {r.status_code}: {r.text[:200]}")
            return False
    except Exception as e:
        logger.warning(f"Resend transport failed: {e}")
        return False


async def _send_via_smtp(to: str, subject: str, html: str) -> bool:
    """Send email via SMTP."""
    smtp_host = os.getenv("SMTP_HOST", "")
    if not smtp_host:
        return False
    try:
        import smtplib
        import email.mime.multipart as _mp
        import email.mime.text as _mt

        msg = _mp.MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = _FROM
        msg["To"] = to
        msg.attach(_mt.MIMEText(html, "html"))

        port = int(os.getenv("SMTP_PORT", "587"))
        user = os.getenv("SMTP_USER", "")
        passwd = os.getenv("SMTP_PASS", "")

        with smtplib.SMTP(smtp_host, port, timeout=15) as s:
            s.ehlo()
            if port == 465:
                # SSL
                import smtplib as _sl
                with _sl.SMTP_SSL(smtp_host, port) as ssl_s:
                    if user:
                        ssl_s.login(user, passwd)
                    ssl_s.send_message(msg)
            else:
                s.starttls()
                if user:
                    s.login(user, passwd)
                s.send_message(msg)

        logger.info(f"Email sent via SMTP: to={to} subject={subject[:50]}")
        return True
    except Exception as e:
        logger.warning(f"SMTP transport failed: {e}")
        return False


async def send_notification_email(
    to_email: str,
    username: str,
    ntype: str,
    title: str,
    body: str,
) -> bool:
    """
    Send a notification email with full VIT HTML branding.

    Tries Resend first (if RESEND_API_KEY is set), then SMTP (if SMTP_HOST is set).
    Falls back to console log in dev.

    Returns True if the email was dispatched successfully.
    """
    subject, html = _build_email_html(ntype, title, body, username)

    # Try Resend first (preferred)
    if os.getenv("RESEND_API_KEY"):
        if await _send_via_resend(to_email, subject, html):
            return True

    # Fallback to SMTP
    if os.getenv("SMTP_HOST"):
        if await _send_via_smtp(to_email, subject, html):
            return True

    # Dev mode: log to console
    logger.info(
        "[email-dev] NOT SENT (no transport configured) "
        f"TO={to_email} SUBJECT={subject} BODY={body[:120]}"
    )
    if os.getenv("ENVIRONMENT") == "development":
        logger.info(f"[MOCK EMAIL] Success response for {to_email}")
        return True
    return False


async def send_test_email(to_email: str, username: str) -> bool:
    """Send a test email to verify delivery is working."""
    return await send_notification_email(
        to_email=to_email,
        username=username,
        ntype="system",
        title="Test Notification — VIT Network",
        body=(
            "This is a test email from VIT Sports Intelligence Network. "
            "If you received this, your email notifications are working correctly."
        ),
    )


# ── Auth email helpers ─────────────────────────────────────────────────────────

def _cta_button(label: str, url: str) -> str:
    return (
        f'<div style="text-align:center;margin:28px 0;">'
        f'<a href="{url}" style="background:{_PRIMARY};color:#000;text-decoration:none;'
        f'font-weight:700;font-size:14px;padding:14px 36px;border-radius:6px;'
        f'display:inline-block;letter-spacing:0.5px;">{label}</a></div>'
        f'<p style="text-align:center;font-size:11px;color:#555;margin:0;">'
        f'Or copy this link: <span style="color:{_PRIMARY};">{url}</span></p>'
    )


async def send_verification_email(
    to_email: str,
    username: str,
    verification_link: str,
    ttl_hours: int = 24,
) -> bool:
    """Send a branded email-verification link."""
    title = "Verify your VIT Network email"
    body_html = f"""
    <p style="margin:0 0 12px;color:#c0c0d8;">Hi {username or 'there'},</p>
    <p style="color:#a0a0b8;font-size:14px;line-height:1.7;margin:0 0 8px;">
      You're almost there! Click the button below to verify your email address
      and unlock full access to the VIT Sports Intelligence Network.
    </p>
    {_cta_button("Verify Email Address", verification_link)}
    <p style="color:#666;font-size:12px;margin:16px 0 0;">
      This link expires in {ttl_hours} hours. If you didn't create a VIT account, you can safely ignore this email.
    </p>
    """
    subject = "🔐 Verify your VIT Network email"
    html = _html_wrapper(title, body_html)

    if os.getenv("RESEND_API_KEY"):
        if await _send_via_resend(to_email, subject, html):
            return True
    if os.getenv("SMTP_HOST"):
        if await _send_via_smtp(to_email, subject, html):
            return True

    logger.info(
        "[email-dev] Verification email NOT SENT (no transport) "
        f"TO={to_email} LINK={verification_link}"
    )
    if os.getenv("ENVIRONMENT") == "development":
        logger.info(f"[MOCK EMAIL] Success response for {to_email}")
        return True
    return False


async def send_password_reset_email(
    to_email: str,
    username: str,
    reset_link: str,
    ttl_hours: int = 2,
) -> bool:
    """Send a branded password-reset link."""
    title = "Reset your VIT Network password"
    body_html = f"""
    <p style="margin:0 0 12px;color:#c0c0d8;">Hi {username or 'there'},</p>
    <p style="color:#a0a0b8;font-size:14px;line-height:1.7;margin:0 0 8px;">
      We received a request to reset the password for your VIT Network account.
      Click the button below to choose a new password.
    </p>
    {_cta_button("Reset My Password", reset_link)}
    <p style="color:#666;font-size:12px;margin:16px 0 0;">
      This link expires in {ttl_hours} hours. If you didn't request a password reset,
      no action is needed — your account is still secure.
    </p>
    """
    subject = "🔑 Reset your VIT Network password"
    html = _html_wrapper(title, body_html)

    if os.getenv("RESEND_API_KEY"):
        if await _send_via_resend(to_email, subject, html):
            return True
    if os.getenv("SMTP_HOST"):
        if await _send_via_smtp(to_email, subject, html):
            return True

    logger.info(
        "[email-dev] Password reset email NOT SENT (no transport) "
        f"TO={to_email} LINK={reset_link}"
    )
    if os.getenv("ENVIRONMENT") == "development":
        logger.info(f"[MOCK EMAIL] Success response for {to_email}")
        return True
    return False
