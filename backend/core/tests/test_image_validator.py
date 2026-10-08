from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from core.testing.images import image_file
from core.validators import MAX_IMAGE_BYTES, validate_image_upload


class ImageValidatorTests(SimpleTestCase):
    def test_accepts_jpeg_png_and_webp(self):
        for image_format, name in (("JPEG", "a.jpg"), ("PNG", "a.png"), ("WEBP", "a.webp")):
            with self.subTest(image_format=image_format):
                upload = image_file(name, image_format)
                validate_image_upload(upload)
                self.assertEqual(upload.tell(), 0)

    def test_rejects_other_formats(self):
        with self.assertRaises(ValidationError):
            validate_image_upload(image_file("a.gif", "GIF"))

    def test_rejects_a_non_image_with_an_image_name(self):
        fake = SimpleUploadedFile("photo.png", b"not an image", content_type="image/png")

        with self.assertRaises(ValidationError):
            validate_image_upload(fake)

    def test_rejects_files_over_2_mb(self):
        upload = image_file("big.png", padding_bytes=MAX_IMAGE_BYTES)

        with self.assertRaisesMessage(ValidationError, "2 MB"):
            validate_image_upload(upload)

    def test_none_is_allowed(self):
        validate_image_upload(None)
