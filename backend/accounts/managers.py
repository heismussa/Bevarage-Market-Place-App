from django.contrib.auth.base_user import BaseUserManager
from django.core.exceptions import ValidationError

from accounts.validators import validate_phone


class UserManager(BaseUserManager):
    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError("A phone number is required.")
        if not password:
            raise ValueError("A password is required.")
        try:
            validate_phone(phone)
        except ValidationError as exc:
            raise ValidationError({"phone": exc.messages}) from exc

        email = extra_fields.get("email")
        if email:
            extra_fields["email"] = self.normalize_email(email).lower()
        else:
            extra_fields["email"] = None

        if "role" not in extra_fields or not extra_fields["role"]:
            raise ValueError("A role is required.")

        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_staff", False)

        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault("role", "ADMIN")
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("role") != "ADMIN":
            raise ValueError("Superuser role must be ADMIN.")
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(phone, password, **extra_fields)
