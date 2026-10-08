from django.core.validators import RegexValidator

validate_phone = RegexValidator(
    regex=r"^\+255\d{9}$",
    message=(
        "Enter a phone number in +255 format followed by 9 digits (for example +255712345678)."
    ),
)
