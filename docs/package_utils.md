These are utils that ship with the package

1. EmailBackend: This is a custom email backend that uses MailerSend to send emails.
   EMAIL_BACKEND = "dj_waanverse_auth.backends.EmailBackend"
   - Requires MailerSend API Key
   - Requires the following settings:
      - DEFAULT_FROM_NAME: str (default: "No Reply")
      - DEFAULT_FROM_EMAIL: str Required and should match the setup domain in MailerSend
      - MAILERSEND_API_KEY: str Required 
   
   This utility uses the same send_mail function as django.core.mail.send_mail but a different backend. It can only send 1 email to one user per time not mass emails

   usage example:
   ```python
   from django.core.mail import send_mail
   send_mail(
      subject="Hello",
      message="Hello, this is a test email.",
      from_email="from@example.com",
      recipient_list=["to@example.com"],
   )
   ```

   or 
   ```python
   from django.core.mail import send_mail
   send_mail(
      subject="Hello",
      message="Hello, this is a test email.",
      from_email="from@example.com",
      recipient_list=[{"email": "to@example.com", "name": "To"}],
   )
   ```
   however the from email will always be the DEFAULT_FROM_EMAIL and the from name will always be the DEFAULT_FROM_NAME but it should be applied to prevent the send_mail function from failing.