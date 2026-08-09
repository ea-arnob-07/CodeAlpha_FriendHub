from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from PIL import Image

validate_extension = FileExtensionValidator(["jpg", "jpeg", "png", "webp"])


def validate_image_upload(upload):
    """Reject oversized or malformed image uploads."""
    validate_extension(upload)
    if upload.size > settings.MAX_UPLOAD_SIZE:
        max_mb = settings.MAX_UPLOAD_SIZE // (1024 * 1024)
        raise ValidationError(f"Image must be smaller than {max_mb} MB.")
    try:
        image = Image.open(upload)
        image.verify()
        upload.seek(0)
    except (OSError, ValueError, SyntaxError) as exc:
        raise ValidationError("Upload a valid JPG, PNG, or WebP image.") from exc
