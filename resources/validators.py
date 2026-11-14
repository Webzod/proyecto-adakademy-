from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


MAX_RESOURCE_FILE_SIZE = 25 * 1024 * 1024


def validate_file_size(file):
    if file.size > MAX_RESOURCE_FILE_SIZE:
        raise ValidationError(
            _("El archivo no puede superar los %(limit)s MB."),
            params={"limit": MAX_RESOURCE_FILE_SIZE // (1024 * 1024)},
        )
