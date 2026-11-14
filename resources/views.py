from pathlib import PurePosixPath

from django.db.models import F
from django.http import FileResponse
from django.shortcuts import get_object_or_404, render

from .models import Materia, RecursoAcademico


def index(request):
    recursos = RecursoAcademico.objects.select_related("materia").all()
    query = request.GET.get("q", "").strip()
    materia_id = request.GET.get("materia", "")

    if query:
        recursos = recursos.filter(titulo__icontains=query)
    if materia_id.isdigit():
        recursos = recursos.filter(materia_id=materia_id)

    return render(
        request,
        "resources/index.html",
        {
            "recursos": recursos,
            "materias": Materia.objects.all(),
            "query": query,
            "materia_seleccionada": materia_id,
        },
    )


def detail(request, pk):
    recurso = get_object_or_404(
        RecursoAcademico.objects.select_related("materia").prefetch_related(
            "comentarios"
        ),
        pk=pk,
    )
    RecursoAcademico.objects.filter(pk=recurso.pk).update(vistas=F("vistas") + 1)
    recurso.refresh_from_db(fields=["vistas"])
    return render(request, "resources/detail.html", {"recurso": recurso})


def download(request, pk):
    recurso = get_object_or_404(RecursoAcademico, pk=pk)
    archivo = recurso.archivo.open("rb")
    RecursoAcademico.objects.filter(pk=recurso.pk).update(
        descargas=F("descargas") + 1
    )
    filename = PurePosixPath(recurso.archivo.name).name
    return FileResponse(
        archivo,
        as_attachment=True,
        filename=filename,
    )
