import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Materia, RecursoAcademico
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


class ResourceManagementTests(TestCase):
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
        self.user = get_user_model().objects.create_user(
            username="gestor",
            password="contraseña-segura-123",
        )

    def tearDown(self):
        self.media_override.disable()
        self.media_dir.cleanup()
        super().tearDown()

    def test_create_requires_login(self):
        response = self.client.get(reverse("resources:create"))

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('resources:create')}",
        )

    def test_create_resource_with_uploaded_file(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("resources:create"),
            {
                "titulo": "Apuntes de biología",
                "descripcion": "Resumen del primer tema.",
                "tipo": RecursoAcademico.Tipo.APUNTE,
                "materia": self.materia.pk,
                "archivo": SimpleUploadedFile("apuntes.pdf", b"nuevo archivo"),
            },
        )

        nuevo_recurso = RecursoAcademico.objects.get(titulo="Apuntes de biología")
        self.assertRedirects(
            response,
            reverse("resources:detail", args=[nuevo_recurso.pk]),
        )
        self.assertTrue(nuevo_recurso.archivo.name.endswith("apuntes.pdf"))

    def test_create_rejects_disallowed_file_extension(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("resources:create"),
            {
                "titulo": "Archivo no permitido",
                "descripcion": "Este archivo debe rechazarse.",
                "tipo": RecursoAcademico.Tipo.GUIA,
                "materia": self.materia.pk,
                "archivo": SimpleUploadedFile("programa.exe", b"contenido"),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "exe")
        self.assertFalse(
            RecursoAcademico.objects.filter(titulo="Archivo no permitido").exists()
        )

    def test_update_preserves_file_when_no_replacement_is_uploaded(self):
        self.client.force_login(self.user)
        archivo_original = self.recurso.archivo.name
        response = self.client.post(
            reverse("resources:update", args=[self.recurso.pk]),
            {
                "titulo": "Guía actualizada",
                "descripcion": "Descripción revisada.",
                "tipo": RecursoAcademico.Tipo.GUIA,
                "materia": self.materia.pk,
            },
        )

        self.assertRedirects(
            response,
            reverse("resources:detail", args=[self.recurso.pk]),
        )
        self.recurso.refresh_from_db()
        self.assertEqual(self.recurso.titulo, "Guía actualizada")
        self.assertEqual(self.recurso.archivo.name, archivo_original)

    def test_delete_requires_confirmation_and_login(self):
        response = self.client.get(reverse("resources:delete", args=[self.recurso.pk]))

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('resources:delete', args=[self.recurso.pk])}",
        )
        self.assertTrue(RecursoAcademico.objects.filter(pk=self.recurso.pk).exists())

    def test_delete_confirmation_page_does_not_delete_resource(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("resources:delete", args=[self.recurso.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "¿Eliminar este recurso?")
        self.assertTrue(RecursoAcademico.objects.filter(pk=self.recurso.pk).exists())

    def test_confirmed_delete_removes_resource_and_uploaded_file(self):
        self.client.force_login(self.user)
        archivo = self.recurso.archivo
        response = self.client.post(
            reverse("resources:delete", args=[self.recurso.pk])
        )

        self.assertRedirects(response, reverse("resources:index"))
        self.assertFalse(RecursoAcademico.objects.filter(pk=self.recurso.pk).exists())
        self.assertFalse(archivo.storage.exists(archivo.name))

        oversized = SimpleUploadedFile(
            "large.pdf",
            b"x" * (MAX_RESOURCE_FILE_SIZE + 1),
        )
        self.recurso.archivo = oversized
        with self.assertRaises(ValidationError):
            self.recurso.full_clean()
