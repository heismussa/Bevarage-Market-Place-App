import io
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image

CONTENT_TYPES = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp", "GIF": "image/gif"}


def image_file(name="image.png", image_format="PNG", size=(8, 8), padding_bytes=0):
    """In-memory image upload. padding_bytes appends junk after the image to inflate its size."""
    buffer = io.BytesIO()
    Image.new("RGB", size, color=(200, 30, 30)).save(buffer, format=image_format)
    content = buffer.getvalue() + b"\0" * padding_bytes
    return SimpleUploadedFile(name, content, content_type=CONTENT_TYPES[image_format])


class TemporaryMediaMixin:
    """Store uploads in a throwaway MEDIA_ROOT for the test class."""

    @classmethod
    def setUpClass(cls):
        cls._media_root = tempfile.mkdtemp(prefix="test-media-")
        cls._media_override = override_settings(MEDIA_ROOT=cls._media_root)
        cls._media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._media_override.disable()
        shutil.rmtree(cls._media_root, ignore_errors=True)
