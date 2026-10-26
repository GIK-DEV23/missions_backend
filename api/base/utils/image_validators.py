"""
Image validation utilities for Django ImageField.

Provides validators for:
- File size limits
- Allowed file types (by extension and content type)
- Image dimensions (max width/height)
"""
from django.core.exceptions import ValidationError
from django.core.validators import BaseValidator
from django.utils.deconstruct import deconstructible


# ── Constants ──────────────────────────────────────────────────────────────────

# Default max file size: 5MB
DEFAULT_MAX_FILE_SIZE = 5 * 1024 * 1024

# Default max dimensions
DEFAULT_MAX_WIDTH = 4096
DEFAULT_MAX_HEIGHT = 4096

# Allowed image extensions and their MIME types
ALLOWED_IMAGE_TYPES = {
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'webp': 'image/webp',
}


# ── Validators ─────────────────────────────────────────────────────────────────

@deconstructible
class FileSizeValidator:
    """
    Validates that an uploaded file does not exceed the specified size.
    
    Usage:
        photo = models.ImageField(validators=[FileSizeValidator(max_bytes=5*1024*1024)])
    """
    
    def __init__(self, max_bytes: int = DEFAULT_MAX_FILE_SIZE):
        self.max_bytes = max_bytes
    
    def __call__(self, file):
        if file.size > self.max_bytes:
            max_mb = self.max_bytes / (1024 * 1024)
            file_mb = file.size / (1024 * 1024)
            raise ValidationError(
                f"File size ({file_mb:.1f}MB) exceeds maximum allowed ({max_mb:.1f}MB).",
                code='file_too_large',
            )
    
    def __eq__(self, other):
        return isinstance(other, FileSizeValidator) and self.max_bytes == other.max_bytes


@deconstructible
class ImageTypeValidator:
    """
    Validates that an uploaded image has an allowed file extension and content type.
    
    Usage:
        photo = models.ImageField(validators=[ImageTypeValidator()])
        # Or with custom types:
        photo = models.ImageField(validators=[ImageTypeValidator(allowed_types={'png': 'image/png'})])
    """
    
    def __init__(self, allowed_types: dict = None):
        self.allowed_types = allowed_types or ALLOWED_IMAGE_TYPES
    
    def __call__(self, file):
        # Check extension
        ext = self._get_extension(file.name)
        if ext not in self.allowed_types:
            allowed = ', '.join(sorted(self.allowed_types.keys()))
            raise ValidationError(
                f"File type '.{ext}' is not allowed. Allowed types: {allowed}.",
                code='invalid_image_type',
            )
        
        # Check content type if available
        if hasattr(file, 'content_type') and file.content_type:
            expected_mime = self.allowed_types[ext]
            # Allow both image/jpeg variations
            if file.content_type not in (expected_mime, 'image/jpg'):
                raise ValidationError(
                    f"File content type '{file.content_type}' does not match extension '.{ext}'.",
                    code='content_type_mismatch',
                )
    
    def _get_extension(self, filename: str) -> str:
        """Extract lowercase extension from filename."""
        if '.' not in filename:
            return ''
        return filename.rsplit('.', 1)[-1].lower()
    
    def __eq__(self, other):
        return isinstance(other, ImageTypeValidator) and self.allowed_types == other.allowed_types


@deconstructible
class ImageDimensionValidator:
    """
    Validates that an uploaded image does not exceed maximum dimensions.
    
    Usage:
        photo = models.ImageField(validators=[ImageDimensionValidator(max_width=4096, max_height=4096)])
    """
    
    def __init__(self, max_width: int = DEFAULT_MAX_WIDTH, max_height: int = DEFAULT_MAX_HEIGHT):
        self.max_width = max_width
        self.max_height = max_height
    
    def __call__(self, file):
        # Only validate if we can read dimensions
        if not hasattr(file, 'image') and hasattr(file, 'file'):
            # Try to get image dimensions from the file
            try:
                from PIL import Image
                file.seek(0)
                img = Image.open(file)
                width, height = img.size
                file.seek(0)
            except Exception:
                # Can't read dimensions, skip validation
                return
        elif hasattr(file, 'width') and hasattr(file, 'height'):
            width = file.width
            height = file.height
        else:
            # Can't determine dimensions
            return
        
        if width and width > self.max_width:
            raise ValidationError(
                f"Image width ({width}px) exceeds maximum allowed ({self.max_width}px).",
                code='image_too_wide',
            )
        
        if height and height > self.max_height:
            raise ValidationError(
                f"Image height ({height}px) exceeds maximum allowed ({self.max_height}px).",
                code='image_too_tall',
            )
    
    def __eq__(self, other):
        return (
            isinstance(other, ImageDimensionValidator) and 
            self.max_width == other.max_width and 
            self.max_height == other.max_height
        )


# ── Composite validator ────────────────────────────────────────────────────────

def get_image_validators(
    max_bytes: int = DEFAULT_MAX_FILE_SIZE,
    max_width: int = DEFAULT_MAX_WIDTH,
    max_height: int = DEFAULT_MAX_HEIGHT,
    allowed_types: dict = None,
):
    """
    Returns a list of image validators with the specified constraints.
    
    Usage:
        photo = models.ImageField(validators=get_image_validators(max_bytes=2*1024*1024))
    
    Args:
        max_bytes: Maximum file size in bytes (default 5MB)
        max_width: Maximum image width in pixels (default 4096)
        max_height: Maximum image height in pixels (default 4096)
        allowed_types: Dict of allowed extensions to MIME types (default: jpg, jpeg, png, webp)
    
    Returns:
        List of validator instances
    """
    return [
        FileSizeValidator(max_bytes=max_bytes),
        ImageTypeValidator(allowed_types=allowed_types),
        ImageDimensionValidator(max_width=max_width, max_height=max_height),
    ]
