from datetime import timedelta
import logging
from pathlib import PurePosixPath

from django.core.paginator import Paginator
from django.db.models import F, Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .forms import ComentarioForm
from .models import RecursoAcademico


logger = logging.getLogger(__name__)
VIEW_COUNT_WINDOW_SECONDS = 30 * 60
VIEW_SESSION_KEY = "resource_views"
FAVORITES_SESSION_KEY = "favorite_resources"
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


def index(request):
    recursos = RecursoAcademico.objects.select_related("materia")
    query = request.GET.get("q", "").strip()
    materia = request.GET.get("materia", "")
    tipo = request.GET.get("tipo", "")
    orden = request.GET.get("orden", "recientes")
    favoritos_solo = request.GET.get("guardados") == "1"

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
    favoritos = request.session.get(FAVORITES_SESSION_KEY, [])
    if not isinstance(favoritos, list):
        favoritos = []
    if favoritos_solo:
        favoritos_validos = [
            resource_id
            for resource_id in favoritos
            if str(resource_id).isdigit()
        ]
        recursos = recursos.filter(pk__in=favoritos_validos)

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
            "favoritos": {str(resource_id) for resource_id in favoritos},
            "favoritos_solo": favoritos_solo,
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
    if request.method == "POST":
        form = ComentarioForm(request.POST)
        if form.is_valid():
            comentario = form.save(commit=False)
            comentario.recurso = recurso
            comentario.save()
            return redirect("resources:detail", pk=recurso.pk)
    else:
        form = ComentarioForm()

    favoritos = request.session.get(FAVORITES_SESSION_KEY, [])
    if not isinstance(favoritos, list):
        favoritos = []
    extension = PurePosixPath(recurso.archivo.name).suffix.lower()
    return render(
        request,
        "resources/detail.html",
        {
            "recurso": recurso,
            "comment_form": form,
            "is_favorite": str(recurso.pk) in {str(resource_id) for resource_id in favoritos},
            "extension": extension,
        },
    )


def toggle_favorite(request, pk):
    recurso = get_object_or_404(RecursoAcademico, pk=pk)
    if request.method == "POST":
        favoritos = request.session.get(FAVORITES_SESSION_KEY, [])
        if not isinstance(favoritos, list):
            favoritos = []
        favoritos = {str(resource_id) for resource_id in favoritos}
        resource_id = str(recurso.pk)
        if resource_id in favoritos:
            favoritos.remove(resource_id)
        else:
            favoritos.add(resource_id)
        request.session[FAVORITES_SESSION_KEY] = sorted(
            favoritos,
            key=int,
        )
    next_url = request.POST.get("next")
    if next_url:
        return redirect(next_url)
    return redirect("resources:detail", pk=recurso.pk)


def download(_request, pk):
    del _request
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
