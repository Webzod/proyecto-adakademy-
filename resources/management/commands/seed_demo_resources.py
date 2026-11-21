from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from resources.models import Materia, RecursoAcademico


class Command(BaseCommand):
    help = "Crea materias y recursos de demostración si faltan."

    def handle(self, *args, **options):
        del args, options
        materias = {
            "Biología": ("Primer semestre", "Ciencias"),
            "Castellano": ("Primer semestre", "Humanidades"),
            "Física": ("Segundo semestre", "Ingeniería"),
            "Inglés": ("Primer semestre", "Idiomas"),
            "Matemáticas": ("Primer semestre", "Ciencias"),
            "Química": ("Segundo semestre", "Ciencias"),
        }
        materia_objects = {}
        for nombre, (semestre, facultad) in materias.items():
            materia_objects[nombre], _ = Materia.objects.get_or_create(
                nombre=nombre,
                defaults={"semestre": semestre, "facultad": facultad},
            )

        desired_materias = [
            ("Biología", "Primer semestre", "Ciencias"),
            ("Castellano", "Primer semestre", "Humanidades"),
            ("Física", "Segundo semestre", "Ingeniería"),
            ("Inglés", "Primer semestre", "Idiomas"),
            ("Matemáticas", "Primer semestre", "Ciencias"),
            ("Química", "Segundo semestre", "Ciencias"),
        ]
        existing_materias = list(Materia.objects.order_by("pk"))
        for materia, values in zip(existing_materias, desired_materias):
            nombre, semestre, facultad = values
            materia.nombre = nombre
            materia.semestre = semestre
            materia.facultad = facultad
            materia.save(update_fields=["nombre", "semestre", "facultad"])
        for materia in materia_objects.values():
            materia.refresh_from_db()

        demos = [
            ("Guía de álgebra básica", "Conceptos, ejemplos y ejercicios resueltos.", "guia", "Matemáticas"),
            ("Apuntes de célula", "Resumen de la estructura y funciones celulares.", "apunte", "Biología"),
            ("Ejercicios de cinemática", "Problemas de movimiento rectilíneo con soluciones.", "clase", "Física"),
            ("Vocabulary essentials", "Lista de vocabulario y expresiones de conversación.", "apunte", "Inglés"),
            ("Ortografía y redacción", "Reglas prácticas y ejemplos para mejorar los textos.", "guia", "Castellano"),
            ("Tabla periódica de repaso", "Notas sobre grupos, períodos y propiedades.", "clase", "Química"),
        ]
        for recurso, (titulo, descripcion, tipo, materia_nombre) in zip(
            RecursoAcademico.objects.order_by("pk"),
            demos,
        ):
            recurso.titulo = titulo
            recurso.descripcion = descripcion
            recurso.tipo = tipo
            recurso.materia = materia_objects[materia_nombre]
            recurso.save(
                update_fields=["titulo", "descripcion", "tipo", "materia"]
            )
        created = 0
        title_patterns = [
            "lgebra",
            "Apuntes",
            "cinem",
            "Vocabulary",
            "Ortograf",
            "Tabla",
        ]
        for titulo, descripcion, tipo, materia_nombre in demos:
            existing = RecursoAcademico.objects.filter(titulo=titulo).first()
            if existing:
                if existing.descripcion != descripcion:
                    existing.descripcion = descripcion
                    existing.save(update_fields=["descripcion"])
                continue

            pattern = title_patterns[demos.index((titulo, descripcion, tipo, materia_nombre))]
            existing = RecursoAcademico.objects.filter(titulo__icontains=pattern).first()
            if existing:
                existing.titulo = titulo
                existing.descripcion = descripcion
                existing.tipo = tipo
                existing.materia = materia_objects[materia_nombre]
                existing.save(update_fields=["titulo", "descripcion", "tipo", "materia"])
                continue

            existing = RecursoAcademico.objects.filter(
                materia=materia_objects[materia_nombre],
                tipo=tipo,
            ).first()
            if existing:
                existing.titulo = titulo
                existing.descripcion = descripcion
                existing.save(update_fields=["titulo", "descripcion"])
                continue
            recurso = RecursoAcademico(
                titulo=titulo,
                descripcion=descripcion,
                tipo=tipo,
                materia=materia_objects[materia_nombre],
            )
            recurso.archivo.save(
                f"{titulo.lower().replace(' ', '-')}.txt",
                ContentFile(descripcion.encode("utf-8")),
                save=True,
            )
            created += 1
        self.stdout.write(self.style.SUCCESS(f"Recursos de demostración creados: {created}"))
