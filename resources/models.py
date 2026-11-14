from django.core.validators import FileExtensionValidator
from django.db import models

from .validators import validate_file_size


class Materia(models.Model):
    nombre = models.CharField(max_length=120)
    semestre = models.CharField(max_length=40)
    facultad = models.CharField(max_length=120)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "materia"
        verbose_name_plural = "materias"

    def __str__(self):
        return self.nombre


class RecursoAcademico(models.Model):
    class Tipo(models.TextChoices):
        GUIA = "guia", "Guía de estudio"
        APUNTE = "apunte", "Apunte"
        MATERIAL_CLASE = "clase", "Material de clase"

    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    tipo = models.CharField(
        max_length=20,
        choices=Tipo.choices,
        default=Tipo.GUIA,
    )
    archivo = models.FileField(
        upload_to="recursos/",
        validators=[
            FileExtensionValidator(
                allowed_extensions=[
                    "csv",
                    "doc",
                    "docx",
                    "jpg",
                    "jpeg",
                    "pdf",
                    "png",
                    "ppt",
                    "pptx",
                    "txt",
                    "xls",
                    "xlsx",
                ]
            ),
            validate_file_size,
        ],
    )
    materia = models.ForeignKey(
        Materia,
        on_delete=models.CASCADE,
        related_name="recursos",
    )
    fecha_subida = models.DateTimeField(auto_now_add=True)
    vistas = models.PositiveIntegerField(default=0)
    descargas = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-fecha_subida"]
        verbose_name = "recurso académico"
        verbose_name_plural = "recursos académicos"

    def __str__(self):
        return self.titulo


class Comentario(models.Model):
    recurso = models.ForeignKey(
        RecursoAcademico,
        on_delete=models.CASCADE,
        related_name="comentarios",
    )
    texto = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "comentario"
        verbose_name_plural = "comentarios"

    def __str__(self):
        return f"Comentario en {self.recurso}"
