# Custom User Model Documentation

This document explains the implementation and usage of the `AbstractBaseAccount` custom user model. This model provides a flexible authentication system that supports both email and phone number as contact methods, while using a username as the primary identifier.

## Key Features

-   Username-based authentication with support for email and phone number
-   Conditional unique constraints for email and phone number
-   Built-in verification status tracking for both email and phone
-   Extensible abstract base class
-   Custom model manager for user creation
-   Password management tracking
-   Comprehensive indexing for optimal query performance

## Implementation

### Basic Usage

To implement the custom user model, create a concrete model that inherits from `AbstractBaseAccount`:

```python
from django.db import models
from path.to.abstract_model import AbstractBaseAccount

class User(AbstractBaseAccount):
    # Add your custom fields here
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)

    class Meta(AbstractBaseAccount.Meta):
        db_table = 'auth_user'
        swappable = 'AUTH_USER_MODEL'
```

### Configuration

In your Django settings:

```python
AUTH_USER_MODEL = 'yourapp.User'
```

## Extending the Model

### Adding Custom Fields

You can add any additional fields to your concrete model:

```python
class User(AbstractBaseAccount):
    birth_date = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    profile_photo = models.ImageField(upload_to='profiles/', null=True, blank=True)
```

### Customizing the Meta Class

The Meta class can be extended while maintaining the base constraints:

```python
class User(AbstractBaseAccount):
    class Meta(AbstractBaseAccount.Meta):
        # Inherit all abstract model constraints and indexes
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']
        permissions = [
            ("can_view_profiles", "Can view user profiles"),
            ("can_edit_profiles", "Can edit user profiles"),
        ]
```

### Adding Custom Methods

Extend functionality by adding custom methods:

```python
class User(AbstractBaseAccount):
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def send_verification_email(self):
        # Implementation for sending verification email
        pass

    def send_verification_sms(self):
        # Implementation for sending verification SMS
        pass
```

## Model Manager Usage

### Creating Regular Users

```python
# Create user with email
user = User.objects.create_user(
    username='johndoe',
    password='secure_password',
    email_address='john@example.com'
)

# Create user with phone
user = User.objects.create_user(
    username='janedoe',
    password='secure_password',
    phone_number='+1234567890'
)
```

### Creating Superusers

```python
superuser = User.objects.create_superuser(
    username='admin',
    password='admin_password',
    email_address='admin@example.com'
)
```

## Validation

The model includes several built-in validations:

1. Username is required and must be unique
2. Either email or phone number must be provided
3. Email and phone number must be unique when provided
4. Custom validations can be added in the concrete model

## Model Constraints

### Built-in Constraints

The model includes conditional unique constraints for email and phone number, allowing them to be optional but unique when provided. These constraints are automatically inherited by concrete models.

### Adding Custom Constraints

```python
class User(AbstractBaseAccount):
    class Meta(AbstractBaseAccount.Meta):
        constraints = [
            *AbstractBaseAccount.Meta.constraints,
            models.CheckConstraint(
                check=models.Q(age__gte=18),
                name='%(app_label)s_%(class)s_adult_age'
            )
        ]
```

## Performance Considerations

-   The model includes optimized indexes for username, email, and phone number lookups
-   Additional indexes can be added based on your specific query patterns
-   The `get_primary_contact` method is implemented as a property for better performance

## Security Features

-   Password updates are tracked via `password_last_updated`
-   Separate verification status for email and phone number
-   Built-in support for Django's permission system
-   Inactive user handling via `is_active` field

## Best Practices

1. Always inherit from AbstractBaseAccount for custom user models
2. Maintain the unique constraints when extending
3. Use the provided manager methods for user creation
4. Implement custom clean methods in concrete models when adding validation
5. Add appropriate indexes for any additional fields used in lookups

## Note on Migrations

When extending this model, remember to:

1. Make migrations after adding new fields or constraints
2. Review generated migrations for correct constraint and index names
3. Handle existing data appropriately when adding new required fields










## Creating Superuser via Shell

Since the default `python manage.py createsuperuser` command doesn't handle custom required fields properly, you can create a superuser through the Django shell. Here's how:

### Method 1: Using Django Shell

```bash
python manage.py shell
```

Then in the Python shell:

```python
# Import your User model - adjust the import path according to your project
from your_app.models import User

# Create superuser with email
user = User.objects.create_user(
    username='admin',
    password='your_secure_password',
    email_address='admin@example.com'  # Required contact method
)

# Make the user a superuser
user.is_superuser = True
user.is_staff = True
user.save()

# Verify the superuser status
print(f"Is superuser: {user.is_superuser}")
print(f"Is staff: {user.is_staff}")
```

### Method 2: Use a Management Command
### Using the Custom Superuser Command

To create a superuser using the custom command:

```bash
# Create superuser with email
python manage.py waanverse-createsuperuser --username admin3 --password secure_password --email admin3@example.com

# Create superuser with phone number
python manage.py waanverse-createsuperuser --username admin4 --password secure_password --phone +1234567890

# Create superuser with email and extra fields
python manage.py waanverse-createsuperuser --username admin5 --password secure_password --email admin5@example.com --extras '{"first_name": "John", "last_name": "Doe"}'

# Create superuser with phone and extra fields
python manage.py waanverse-createsuperuser --username admin6 --password secure_password --phone +1234567890 --extras '{"department": "IT", "location": "HQ"}'
```

#### Command Arguments

- `--username`: (Required) The username for the superuser
- `--password`: (Required) The password for the superuser
- `--email`: (Optional) Email address for the superuser
- `--phone`: (Optional) Phone number for the superuser
- `--extras`: (Optional) JSON string containing additional fields

Note: Either `--email` or `--phone` must be provided, but not necessarily both.
### Verifying Superuser Creation

You can verify the superuser was created correctly:

```python
# In Django shell
from your_app.models import User

# Check user exists and has correct permissions
user = User.objects.get(username='admin')
print(f"Is superuser: {user.is_superuser}")
print(f"Is staff: {user.is_staff}")
print(f"Contact method: {user.get_primary_contact}")
```

### Important Notes

1. Always use strong passwords in production
2. Store sensitive credentials securely
3. Consider implementing proper logging for superuser creation
4. Remember to handle exceptions appropriately in production code
5. Consider adding additional validation in the management command




