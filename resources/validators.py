from django.core.exceptions import ValidationError
from django.db.models.fields.files import FieldFile
from django.utils.translation import gettext_lazy as _
from pathlib import PurePosixPath
import zipfile


MAX_RESOURCE_FILE_SIZE = 25 * 1024 * 1024

ALLOWED_RESOURCE_SIGNATURES = {
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".pdf": (b"%PDF-",),
}


def validate_resource_content(file):
    extension = PurePosixPath(getattr(file, "name", "")).suffix.lower()
    opened_here = isinstance(file, FieldFile) and file._file is None
    try:
        try:
            file.seek(0)
            header = file.read(4096)
            file.seek(0)
        except (OSError, AttributeError):
            raise ValidationError(
                _("No se pudo leer el contenido del archivo.")
            )

        signatures = ALLOWED_RESOURCE_SIGNATURES.get(extension)
        if signatures:
            if not header.startswith(signatures):
                raise ValidationError(
                    _("El contenido no corresponde al tipo de archivo seleccionado.")
                )
        elif extension in {"csv", "txt"}:
            try:
                header.decode("utf-8")
            except UnicodeDecodeError:
                raise ValidationError(
                    _("El archivo de texto debe usar codificación UTF-8.")
                )
        elif extension in {"doc", "xls", "ppt"}:
            return
        elif extension in {"docx", "xlsx", "pptx"}:
            try:
                file.seek(0)
                with zipfile.ZipFile(file) as archive:
                    if not archive.namelist():
                        raise ValidationError(
                            _("El archivo de Office está vacío o es inválido.")
                        )
            except (zipfile.BadZipFile, OSError):
                raise ValidationError(
                    _("El archivo de Office está vacío o es inválido.")
                )
            finally:
                file.seek(0)
    finally:
        if opened_here and file._file is not None:
            file.close()


def validate_file_size(file):
    if file.size > MAX_RESOURCE_FILE_SIZE:
        raise ValidationError(
            _("El archivo no puede superar los %(limit)s MB."),
            params={"limit": MAX_RESOURCE_FILE_SIZE // (1024 * 1024)},
        )
