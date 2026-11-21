from pathlib import PurePosixPath
import zipfile

from PIL import Image, UnidentifiedImageError
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


MAX_RESOURCE_FILE_SIZE = 25 * 1024 * 1024
LEGACY_OFFICE_SIGNATURE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
OFFICE_REQUIRED_PARTS = {
    ".docx": "word/document.xml",
    ".xlsx": "xl/workbook.xml",
    ".pptx": "ppt/presentation.xml",
}
IMAGE_FORMATS = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
}


def validate_resource_content(file):
    extension = PurePosixPath(getattr(file, "name", "")).suffix.lower()
    try:
        file.seek(0)
    except (OSError, AttributeError):
        raise ValidationError(_("No se pudo leer el contenido del archivo."))

    try:
        if extension in IMAGE_FORMATS:
            with Image.open(file) as image:
                if image.format != IMAGE_FORMATS[extension]:
                    raise ValidationError(
                        _("El contenido no corresponde al tipo de archivo seleccionado.")
                    )
                image.verify()
        elif extension == ".pdf":
            content = file.read()
            if (
                b"%PDF-" not in content[:1024]
                or b"%%EOF" not in content[-2048:]
            ):
                raise ValidationError(
                    _("El archivo PDF está incompleto o no es válido.")
                )
        elif extension in OFFICE_REQUIRED_PARTS:
            with zipfile.ZipFile(file) as archive:
                required_parts = {
                    "[Content_Types].xml",
                    OFFICE_REQUIRED_PARTS[extension],
                }
                if not required_parts.issubset(archive.namelist()):
                    raise ValidationError(
                        _("El archivo de Office está incompleto o no es válido.")
                    )
        elif extension in {".doc", ".xls", ".ppt"}:
            if file.read(8) != LEGACY_OFFICE_SIGNATURE:
                raise ValidationError(
                    _("El contenido no corresponde a un documento de Office válido.")
                )
        elif extension in {".csv", ".txt"}:
            file.read().decode("utf-8-sig")
        else:
            raise ValidationError(
                _("El contenido no corresponde al tipo de archivo seleccionado.")
            )
    except UnicodeDecodeError:
        raise ValidationError(_("El archivo de texto debe usar codificación UTF-8."))
    except (
        zipfile.BadZipFile,
        OSError,
        UnidentifiedImageError,
        Image.DecompressionBombError,
        SyntaxError,
    ):
        raise ValidationError(_("El archivo está dañado o no tiene un formato válido."))
    finally:
        try:
            file.seek(0)
        except (OSError, AttributeError):
            raise ValidationError(_("No se pudo volver a leer el archivo."))


def validate_file_size(file):
    if file.size > MAX_RESOURCE_FILE_SIZE:
        raise ValidationError(
            _("El archivo no puede superar los %(limit)s MB."),
            params={"limit": MAX_RESOURCE_FILE_SIZE // (1024 * 1024)},
        )
