# API Endpoints

!!! note "Explanation of Messages"

    The `Messages.___` placeholders, followed by an asterisk (`*`), represent predefined messages that are configured to be returned under various circumstances. These messages are informative and intended to be displayed to end users, providing them with relevant feedback based on the outcome of their requests.

## URL Authentication Requirements

| **Route**                         | **Requires Authentication** |
|-----------------------------------|-----------------------------|
| `/login`                          | No                          |
| `/token/refresh`                  | No                          |
| `/resend/email`                   | No                          |
| `/verify/email`                   | No                          |
| `/signup`                         | No                          |
| `/me`                             | Yes                         |
| `/mfa/activate`                   | Yes                         |
| `/mfa/verify`                     | Yes                         |
| `/mfa/status`                     | Yes                         |
| `/mfa/regenerate-codes`           | Yes                         |
| `/mfa/deactivate`                 | Yes                         |
| `/logout`                         | Yes                         |
| `/mfa/login`                      | Yes                         |
| `/password/reset`                 | No                          |
| `/password/reset/new`             | No                          |
