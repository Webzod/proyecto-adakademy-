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

        demos = [
            ("Guía de álgebra básica", "Conceptos, ejemplos y ejercicios resueltos.", "guia", "Matemáticas"),
            ("Apuntes de célula", "Resumen de la estructura y funciones celulares.", "apunte", "Biología"),
            ("Ejercicios de cinemática", "Problemas de movimiento rectilíneo con soluciones.", "clase", "Física"),
            ("Vocabulary essentials", "Lista de vocabulario y expresiones de conversación.", "apunte", "Inglés"),
            ("Ortografía y redacción", "Reglas prácticas y ejemplos para mejorar los textos.", "guia", "Castellano"),
            ("Tabla periódica de repaso", "Notas sobre grupos, períodos y propiedades.", "clase", "Química"),
        ]
        created = 0
        for titulo, descripcion, tipo, materia_nombre in demos:
            if RecursoAcademico.objects.filter(titulo=titulo).exists():
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
