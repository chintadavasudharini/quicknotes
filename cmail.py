import smtplib
from email.message import EmailMessage
import os
from flask import flash, has_request_context


def send_mail(to, subject, body):
    try:
        email_user = os.getenv('EMAIL_USER')  # your Gmail address
        email_pass = os.getenv('EMAIL_PASS')  # your Gmail App password
    
        if not email_user or not email_pass:
            print("\n" + "=" * 80)
            print(" [DEVELOPMENT MODE] EMAIL SIMULATION ")
            print("=" * 80)
            print(f"To:      {to}")
            print(f"Subject: {subject}")
            print(f"Content:\n{body}")
            print("=" * 80)
            print(" To send actual emails, define EMAIL_USER and EMAIL_PASS in your environment or .env file.")
            print("=" * 80 + "\n")
            
            if has_request_context():
                flash("⚠️ Development Mode: Email credentials not set. Simulated email containing your OTP/link has been printed to the terminal console.", "warning")
            return False

        msg = EmailMessage()
        msg['From'] = email_user
        msg['To'] = to
        msg['Subject'] = subject
        msg.set_content(body)

        # Use context manager for SMTP
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(email_user, email_pass)
            server.send_message(msg)

        print(f"Email sent successfully to {to}")
        return True

    except Exception as e:
        print(f"Error sending email: {e}")
        raise e
