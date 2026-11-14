import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from .models import Materia, RecursoAcademico


class ResourceReadTests(TestCase):
    def setUp(self):
        self.media_dir = tempfile.TemporaryDirectory()
        self.media_override = override_settings(MEDIA_ROOT=self.media_dir.name)
        self.media_override.enable()
        self.materia = Materia.objects.create(
            nombre="Álgebra",
            semestre="Primer semestre",
            facultad="Ciencias",
        )
        self.recurso = RecursoAcademico.objects.create(
            titulo="Guía de álgebra",
            descripcion="Ejercicios de práctica.",
            materia=self.materia,
            archivo=SimpleUploadedFile(
                "guia.pdf",
                b"contenido de prueba",
                content_type="application/pdf",
            ),
        )

    def tearDown(self):
        self.media_override.disable()
        self.media_dir.cleanup()
        super().tearDown()

    def test_index_filters_by_title_and_materia(self):
        response = self.client.get(
            "/",
            {"q": "álgebra", "materia": str(self.materia.pk)},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.recurso.titulo)

    def test_detail_increments_view_count(self):
        response = self.client.get(f"/recurso/{self.recurso.pk}/")

        self.assertEqual(response.status_code, 200)
        self.recurso.refresh_from_db()
        self.assertEqual(self.recurso.vistas, 1)

    def test_download_returns_file_and_increments_download_count(self):
        response = self.client.get(f"/recurso/{self.recurso.pk}/descargar/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            b"".join(response.streaming_content),
            b"contenido de prueba",
        )
        self.recurso.refresh_from_db()
        self.assertEqual(self.recurso.descargas, 1)
        filename = self.recurso.archivo.name.rsplit("/", 1)[-1]
        self.assertIn(filename, response["Content-Disposition"])
