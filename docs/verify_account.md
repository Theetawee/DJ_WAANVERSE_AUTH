required

1. identifier,
2. delivery (code or link) optional default: code

Can configure email subject using ACCOUNT_VERIFICATION_EMAIL_SUBJECT.

Configure custom sms sender function which takes in phone_number and code `SMS_SENDER`
Configure custom frontend url for link `FRONTEND_URL` will always be link/verify?token=token

configure email templates by overriding them at templates/emails/account_verification_code.html
or account_verification_link.html

context is account, code or verify_url
