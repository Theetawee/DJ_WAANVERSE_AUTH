# API Endpoints

!!! note "Explanation of Messages"

    The `Messages.___` placeholders, followed by an asterisk (`*`), represent predefined messages that are configured to be returned under various circumstances. These messages are informative and intended to be displayed to end users, providing them with relevant feedback based on the outcome of their requests.

## URL Authentication Requirements

| **Route**                         | **Requires Authentication** |
|-----------------------------------|-----------------------------|
| `/login`                          | No                          |
| `/token/refresh`                  | Required                    |
| `/resend/email`                   | No                          |
| `/verify/email`                   | No                          |
| `/signup`                         | No                          |
| `/me`                             | Required                    |
| `/mfa/activate`                   | Required                    |
| `/mfa/verify`                     | Required                    |
| `/mfa/status`                     | Required                    |
| `/mfa/regenerate-codes`           | Required                    |
| `/mfa/deactivate`                 | Required                    |
| `/logout`                         | Required                    |
| `/mfa/login`                      | Required                    |
| `/password/reset`                 | No                          |
| `/password/reset/new`             | No                          |