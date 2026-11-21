from datetime import timedelta
import logging
from pathlib import PurePosixPath

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import F, Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .forms import RegistroForm, RecursoAcademicoForm
from .models import RecursoAcademico


logger = logging.getLogger(__name__)
VIEW_COUNT_WINDOW_SECONDS = 30 * 60
VIEW_SESSION_KEY = "resource_views"
SORT_OPTIONS = {
    "recientes": ("-fecha_subida", "-pk"),
    "populares": ("-vistas", "-fecha_subida", "-pk"),
    "titulo": ("titulo", "pk"),
}
PAGE_SIZE = 12
SUBJECTS = (
    "Biología",
    "Castellano",
    "Física",
    "Inglés",
    "Matemáticas",
    "Química",
)


def register(request):
    if request.user.is_authenticated:
        return redirect("resources:index")

    form = RegistroForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(
            request,
            "Tu cuenta está lista. ¡Te damos la bienvenida a Aula Abierta!",
        )
        return redirect("resources:index")

    return render(request, "registration/register.html", {"form": form})


def index(request):
    recursos = RecursoAcademico.objects.select_related("materia")
    query = request.GET.get("q", "").strip()
    materia = request.GET.get("materia", "")
    tipo = request.GET.get("tipo", "")
    orden = request.GET.get("orden", "recientes")

    valid_types = {value for value, _ in RecursoAcademico.Tipo.choices}
    if tipo not in valid_types:
        tipo = ""
    if materia not in SUBJECTS:
        materia = ""

    if query:
        recursos = recursos.filter(
            Q(titulo__icontains=query)
            | Q(descripcion__icontains=query)
            | Q(materia__nombre__icontains=query)
            | Q(materia__facultad__icontains=query)
        )
    if materia:
        recursos = recursos.filter(materia__nombre__iexact=materia)
    if tipo:
        recursos = recursos.filter(tipo=tipo)

    if orden not in SORT_OPTIONS:
        orden = "recientes"
    recursos = recursos.order_by(*SORT_OPTIONS[orden])
    page_obj = Paginator(recursos, PAGE_SIZE).get_page(request.GET.get("page"))

    return render(
        request,
        "resources/index.html",
        {
            "page_obj": page_obj,
            "materias": SUBJECTS,
            "tipos_recurso": RecursoAcademico.Tipo.choices,
            "query": query,
            "materia_seleccionada": materia,
            "tipo_seleccionado": tipo,
            "orden": orden,
        },
    )


def detail(request, pk):
    recurso = get_object_or_404(
        RecursoAcademico.objects.select_related("materia").prefetch_related(
            "comentarios"
        ),
        pk=pk,
    )
    now = timezone.now()
    viewed_resources = request.session.get(VIEW_SESSION_KEY, {})
    if not isinstance(viewed_resources, dict):
        viewed_resources = {}
    cutoff = now - timedelta(seconds=VIEW_COUNT_WINDOW_SECONDS)
    recent_views = {
        resource_id: timestamp
        for resource_id, timestamp in viewed_resources.items()
        if (last_viewed := parse_datetime(timestamp)) is not None
        and timezone.is_aware(last_viewed)
        and last_viewed >= cutoff
    }
    if str(recurso.pk) not in recent_views:
        recent_views[str(recurso.pk)] = now.isoformat()
        request.session[VIEW_SESSION_KEY] = recent_views
        RecursoAcademico.objects.filter(pk=recurso.pk).update(vistas=F("vistas") + 1)
        recurso.vistas += 1
    elif recent_views != viewed_resources:
        request.session[VIEW_SESSION_KEY] = recent_views
    return render(request, "resources/detail.html", {"recurso": recurso})


@login_required
def resource_create(request):
    form = RecursoAcademicoForm(
        request.POST if request.method == "POST" else None,
        request.FILES if request.method == "POST" else None,
    )
    if request.method == "POST" and form.is_valid():
        recurso = form.save()
        messages.success(request, "El recurso se publicó correctamente.")
        return redirect("resources:detail", pk=recurso.pk)

    return render(
        request,
        "resources/resource_form.html",
        {"form": form, "is_edit": False},
    )


@login_required
def resource_update(request, pk):
    recurso = get_object_or_404(RecursoAcademico, pk=pk)
    archivo_anterior = recurso.archivo.name
    form = RecursoAcademicoForm(
        request.POST if request.method == "POST" else None,
        request.FILES if request.method == "POST" else None,
        instance=recurso,
    )
    if request.method == "POST" and form.is_valid():
        recurso = form.save()
        if recurso.archivo.name != archivo_anterior:
            try:
                recurso.archivo.storage.delete(archivo_anterior)
            except OSError:
                logger.exception(
                    "No se pudo eliminar el archivo anterior del recurso %s",
                    recurso.pk,
                )
        messages.success(request, "Los cambios se guardaron correctamente.")
        return redirect("resources:detail", pk=recurso.pk)

    return render(
        request,
        "resources/resource_form.html",
        {"form": form, "is_edit": True, "recurso": recurso},
    )


@login_required
def resource_delete(request, pk):
    recurso = get_object_or_404(RecursoAcademico, pk=pk)
    if request.method == "POST":
        archivo = recurso.archivo
        recurso_id = recurso.pk
        recurso.delete()
        try:
            archivo.storage.delete(archivo.name)
        except OSError:
            logger.exception(
                "No se pudo eliminar el archivo del recurso %s",
                recurso_id,
            )
        messages.success(request, "El recurso se eliminó correctamente.")
        return redirect("resources:index")

    return render(
        request,
        "resources/resource_confirm_delete.html",
        {"recurso": recurso},
    )


def download(request, pk):
    recurso = get_object_or_404(RecursoAcademico, pk=pk)
    try:
        archivo = recurso.archivo.open("rb")
    except (OSError, ValueError) as exc:
        logger.warning(
            "No se pudo abrir el archivo del recurso %s",
            recurso.pk,
        )
        raise Http404("El archivo de este recurso ya no está disponible.") from exc

    RecursoAcademico.objects.filter(pk=recurso.pk).update(
        descargas=F("descargas") + 1
    )
    filename = PurePosixPath(recurso.archivo.name).name
    return FileResponse(
        archivo,
        as_attachment=True,
        filename=filename,
    )
