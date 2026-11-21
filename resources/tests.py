import tempfile
from io import BytesIO
from pathlib import Path
import zipfile

from PIL import Image
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Comentario, Materia, RecursoAcademico
from .validators import MAX_RESOURCE_FILE_SIZE


class ResourceReadTests(TestCase):
    def setUp(self):
        self.media_dir = tempfile.TemporaryDirectory()
        self.media_override = override_settings(MEDIA_ROOT=self.media_dir.name)
        self.media_override.enable()
        self.materia = Materia.objects.create(
            nombre="Biología",
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

    def test_search_matches_description_and_faculty(self):
        response = self.client.get("/", {"q": "práctica"})
        self.assertContains(response, self.recurso.titulo)

        response = self.client.get("/", {"q": "ciencias"})
        self.assertContains(response, self.recurso.titulo)

    def test_index_filters_by_title_and_materia(self):
        response = self.client.get(
            "/",
            {"q": "álgebra", "materia": "Biología"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.recurso.titulo)

    def test_index_filters_by_resource_type(self):
        RecursoAcademico.objects.create(
            titulo="Resumen de álgebra",
            descripcion="Apuntes de las clases.",
            tipo=RecursoAcademico.Tipo.APUNTE,
            materia=self.materia,
            archivo=SimpleUploadedFile("apuntes.pdf", b"contenido"),
        )

        response = self.client.get("/", {"tipo": RecursoAcademico.Tipo.APUNTE})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Resumen de álgebra")
        self.assertNotContains(response, self.recurso.titulo)

    def test_subject_filter_uses_neutral_placeholder(self):
        Materia.objects.create(
            nombre="Todas las materias",
            semestre="General",
            facultad="General",
        )

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, ">Materia</option>")
        self.assertNotContains(response, ">Todas las materias</option>")

    def test_subjects_are_displayed_in_requested_alphabetical_order(self):
        response = self.client.get("/")

        self.assertEqual(
            response.context["materias"],
            (
                "Biología",
                "Castellano",
                "Física",
                "Inglés",
                "Matemáticas",
                "Química",
            ),
        )
        self.assertContains(response, '<option value="Biología"')

    def test_detail_identifies_resource_type_and_contents(self):
        self.recurso.tipo = RecursoAcademico.Tipo.MATERIAL_CLASE
        self.recurso.save(update_fields=["tipo"])

        response = self.client.get(reverse("resources:detail", args=[self.recurso.pk]))

        self.assertContains(response, "Material de clase")
        self.assertContains(response, "Qué incluye este material")
        self.assertContains(response, self.recurso.descripcion)

    def test_view_count_only_increments_once_per_session_window(self):
        url = reverse("resources:detail", args=[self.recurso.pk])
        first_response = self.client.get(url)
        second_response = self.client.get(url)

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.recurso.refresh_from_db()
        self.assertEqual(self.recurso.vistas, 1)

    def test_download_returns_file_and_increments_download_count(self):
        response = self.client.get(
            reverse("resources:download", args=[self.recurso.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            b"".join(response.streaming_content),
            b"contenido de prueba",
        )
        self.recurso.refresh_from_db()
        self.assertEqual(self.recurso.descargas, 1)
        self.assertIn(Path(self.recurso.archivo.name).name, response["Content-Disposition"])

    def test_missing_download_file_returns_404_without_increment(self):
        self.recurso.archivo.delete(save=False)

        response = self.client.get(
            reverse("resources:download", args=[self.recurso.pk])
        )

        self.assertEqual(response.status_code, 404)
        self.recurso.refresh_from_db()
        self.assertEqual(self.recurso.descargas, 0)

    def test_pagination_preserves_search_and_sort_filters(self):
        for number in range(12):
            RecursoAcademico.objects.create(
                titulo=f"Guía adicional {number}",
                descripcion="Material de consulta.",
                materia=self.materia,
                archivo=SimpleUploadedFile(f"guia-{number}.pdf", b"contenido"),
            )

        response = self.client.get(
            "/",
            {
                "q": "guía",
                "materia": self.materia.pk,
                "tipo": RecursoAcademico.Tipo.GUIA,
                "orden": "titulo",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].paginator.count, 13)
        self.assertEqual(len(response.context["page_obj"].object_list), 12)
        self.assertContains(response, "orden=titulo")
        self.assertContains(response, "tipo=guia")
        self.assertContains(response, "page=2")

    def test_invalid_page_falls_back_to_first_page(self):
        response = self.client.get("/", {"page": "not-a-page"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].number, 1)

    def test_file_extension_and_size_are_validated(self):
        self.recurso.archivo = SimpleUploadedFile("script.exe", b"bad")
        with self.assertRaises(ValidationError):
            self.recurso.full_clean()

        oversized = SimpleUploadedFile(
            "large.pdf",
            b"x" * (MAX_RESOURCE_FILE_SIZE + 1),
        )
        self.recurso.archivo = oversized
        with self.assertRaises(ValidationError):
            self.recurso.full_clean()

    def test_user_can_publish_comment(self):
        response = self.client.post(
            reverse("resources:detail", args=[self.recurso.pk]),
            {"texto": "Este recurso fue muy útil."},
        )

        self.assertRedirects(
            response,
            reverse("resources:detail", args=[self.recurso.pk]),
        )
        self.assertTrue(
            Comentario.objects.filter(
                recurso=self.recurso,
                texto="Este recurso fue muy útil.",
            ).exists()
        )

    def test_comment_cannot_be_empty(self):
        response = self.client.post(
            reverse("resources:detail", args=[self.recurso.pk]),
            {"texto": "   "},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Comentario.objects.exists())

    def test_resource_can_be_saved_and_unsaved_in_session(self):
        url = reverse("resources:favorite", args=[self.recurso.pk])
        first_response = self.client.post(url, {"next": "/"})
        second_response = self.client.post(url, {"next": "/"})

        self.assertRedirects(first_response, "/")
        self.assertRedirects(second_response, "/")
        self.assertNotIn(
            str(self.recurso.pk),
            self.client.session["favorite_resources"],
        )

    def test_favorite_rejects_external_redirect(self):
        response = self.client.post(
            reverse("resources:favorite", args=[self.recurso.pk]),
            {"next": "https://example.com"},
        )

        self.assertRedirects(
            response,
            reverse("resources:detail", args=[self.recurso.pk]),
        )

    def test_comment_rejects_excessive_length(self):
        response = self.client.post(
            reverse("resources:detail", args=[self.recurso.pk]),
            {"texto": "a" * 2001},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "2000")
        self.assertFalse(Comentario.objects.exists())

    def test_comment_rate_limit(self):
        url = reverse("resources:detail", args=[self.recurso.pk])
        for number in range(5):
            response = self.client.post(url, {"texto": f"Comentario {number}"})
            self.assertEqual(response.status_code, 302)

        response = self.client.post(url, {"texto": "Último comentario"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "publicado varios comentarios muy rápido")
        self.assertEqual(Comentario.objects.count(), 5)

    def test_resource_file_content_must_match_extension(self):
        self.recurso.archivo = SimpleUploadedFile("imagen.png", b"no es una imagen")
        with self.assertRaises(ValidationError):
            self.recurso.full_clean()

    def test_valid_png_passes_content_validation(self):
        image_buffer = BytesIO()
        Image.new("RGB", (2, 2), color="blue").save(image_buffer, format="PNG")
        self.recurso.archivo = SimpleUploadedFile(
            "imagen.png",
            image_buffer.getvalue(),
            content_type="image/png",
        )

        self.recurso.full_clean()

    def test_invalid_pdf_and_office_archives_are_rejected(self):
        self.recurso.archivo = SimpleUploadedFile(
            "archivo.pdf",
            b"%PDF-1.7\ncontenido sin fin de archivo",
        )
        with self.assertRaises(ValidationError):
            self.recurso.full_clean()

    def test_valid_pdf_and_office_archive_pass_content_validation(self):
        self.recurso.archivo = SimpleUploadedFile(
            "archivo.pdf",
            b"%PDF-1.7\ncontenido\n%%EOF",
        )
        self.recurso.full_clean()

        office_buffer = BytesIO()
        with zipfile.ZipFile(office_buffer, "w") as archive:
            archive.writestr("[Content_Types].xml", "<Types/>")
            archive.writestr("word/document.xml", "<document/>")
        self.recurso.archivo = SimpleUploadedFile(
            "documento.docx",
            office_buffer.getvalue(),
        )
        self.recurso.full_clean()

    def test_text_validation_checks_the_entire_file(self):
        self.recurso.archivo = SimpleUploadedFile(
            "notas.txt",
            b"texto valido " * 400 + b"\xff",
        )

        with self.assertRaises(ValidationError):
            self.recurso.full_clean()

    def test_saved_resources_pagination_preserves_filter(self):
        self.client.post(
            reverse("resources:favorite", args=[self.recurso.pk]),
            {"next": "/"},
        )
        for number in range(12):
            saved = RecursoAcademico.objects.create(
                titulo=f"Guardado {number}",
                descripcion="Material guardado.",
                materia=self.materia,
                archivo=SimpleUploadedFile(f"guardado-{number}.pdf", b"%PDF-fake"),
            )
            self.client.post(
                reverse("resources:favorite", args=[saved.pk]),
                {"next": "/"},
            )

        response = self.client.get("/", {"guardados": "1", "page": "2"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "guardados=1")

    def test_detail_back_link_preserves_index_filters(self):
        self.client.get("/", {"q": "álgebra", "materia": "Biología"})

        response = self.client.get(
            reverse("resources:detail", args=[self.recurso.pk])
        )

        self.assertEqual(
            response.context["back_url"],
            "/?q=%C3%A1lgebra&materia=Biolog%C3%ADa",
        )

    def test_combined_filters_and_sort_are_applied(self):
        RecursoAcademico.objects.create(
            titulo="Guía avanzada",
            descripcion="Ejercicios de práctica.",
            tipo=RecursoAcademico.Tipo.GUIA,
            materia=self.materia,
            archivo=SimpleUploadedFile("avanzada.pdf", b"%PDF-fake"),
        )

        response = self.client.get(
            "/",
            {
                "q": "guía",
                "materia": "Biología",
                "tipo": RecursoAcademico.Tipo.GUIA,
                "orden": "titulo",
            },
        )

        titles = [
            resource.titulo
            for resource in response.context["page_obj"].object_list
        ]
        self.assertIn("Guía de álgebra", titles)
        self.assertIn("Guía avanzada", titles)
        self.assertEqual(titles, sorted(titles, key=str.casefold))

    def test_filter_controls_submit_automatically(self):
        response = self.client.get("/")

        self.assertContains(
            response,
            'document.querySelectorAll(\'form[method="get"] select\')',
        )

    def test_search_matches_accentless_and_resource_type(self):
        response = self.client.get("/", {"q": "guia"})
        self.assertContains(response, "Guía de álgebra")

        response = self.client.get("/", {"q": "estudio"})
        self.assertContains(response, "Guía de álgebra")

    def test_search_matches_plural_and_terms_across_resource_fields(self):
        response = self.client.get("/", {"q": "guías biología"})
        self.assertContains(response, "Guía de álgebra")

    def test_search_matches_plural_apuntes_with_singular_title(self):
        RecursoAcademico.objects.create(
            titulo="Apunte de historia",
            descripcion="Material de consulta.",
            tipo=RecursoAcademico.Tipo.APUNTE,
            materia=self.materia,
            archivo=SimpleUploadedFile("historia.txt", b"contenido"),
        )

        response = self.client.get("/", {"q": "apuntes"})

        self.assertContains(response, "Apunte de historia")

    def test_search_matches_filename(self):
        self.recurso.archivo.name = "recursos/material-examen.pdf"
        self.recurso.save(update_fields=["archivo"])

        response = self.client.get("/", {"q": "examen"})

        self.assertContains(response, self.recurso.titulo)

    def test_apuntes_search_matches_title(self):
        RecursoAcademico.objects.create(
            titulo="Apuntes de célula",
            descripcion="Resumen celular.",
            tipo=RecursoAcademico.Tipo.APUNTE,
            materia=self.materia,
            archivo=SimpleUploadedFile("apuntes.txt", b"contenido"),
        )

        response = self.client.get("/", {"q": "apuntes"})

        self.assertContains(response, "Apuntes de célula")

    def test_skip_navigation_link_is_not_rendered(self):
        response = self.client.get("/")

        self.assertNotContains(response, "Saltar al contenido principal")

    def test_saved_resources_filter(self):
        self.client.post(
            reverse("resources:favorite", args=[self.recurso.pk]),
            {"next": "/"},
        )
        RecursoAcademico.objects.create(
            titulo="Otro recurso",
            descripcion="Material diferente.",
            materia=self.materia,
            archivo=SimpleUploadedFile("otro.pdf", b"contenido"),
        )

        response = self.client.get("/", {"guardados": "1"})

        self.assertContains(response, self.recurso.titulo)
        self.assertNotContains(response, "Otro recurso")
