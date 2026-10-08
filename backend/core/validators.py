from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

MAX_IMAGE_BYTES = 2 * 1024 * 1024
ALLOWED_IMAGE_FORMATS = frozenset({"JPEG", "PNG", "WEBP"})


def validate_image_upload(file):
    """Accept only real JPEG, PNG or WebP images of at most 2 MB.

    The file content is inspected with Pillow; the extension alone is not trusted.
    """
    if file is None:
        return

    if file.size > MAX_IMAGE_BYTES:
        raise ValidationError("Image must be 2 MB or smaller.", code="image_too_large")

    try:
        file.seek(0)
        with Image.open(file) as image:
            image_format = image.format
            image.verify()
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
        raise ValidationError(
            "Upload a valid JPEG, PNG or WebP image.", code="invalid_image"
        ) from exc
    finally:
        file.seek(0)

    if image_format not in ALLOWED_IMAGE_FORMATS:
        raise ValidationError("Upload a valid JPEG, PNG or WebP image.", code="invalid_image")
