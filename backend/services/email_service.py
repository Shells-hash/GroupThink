import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from backend.config import get_settings

settings = get_settings()


def send_reset_email(to_email: str, username: str, reset_token: str) -> None:
    """Send a password reset email via Gmail SMTP. Runs in a background thread."""
    if not settings.gmail_user or not settings.gmail_app_password:
        print(f"[DEV] Password reset link for {username}: "
              f"{settings.base_url}/#/reset-password?token={reset_token}")
        return

    reset_url = f"{settings.base_url}/#/reset-password?token={reset_token}"

    html = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px">
      <h2 style="color:#6c63ff;margin-bottom:8px">Reset your GroupThink password</h2>
      <p style="color:#555;margin-bottom:24px">Hi {username}, click the button below to reset your password.
      This link expires in <strong>1 hour</strong> and can only be used once.</p>
      <a href="{reset_url}"
         style="display:inline-block;background:#6c63ff;color:#fff;padding:12px 28px;
                border-radius:8px;text-decoration:none;font-weight:600">
        Reset Password
      </a>
      <p style="color:#999;font-size:12px;margin-top:24px">
        If you didn't request this, you can safely ignore this email.
      </p>
    </div>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Reset your GroupThink password"
    msg["From"] = settings.gmail_user
    msg["To"] = to_email
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(settings.gmail_user, settings.gmail_app_password)
        server.sendmail(settings.gmail_user, to_email, msg.as_string())
