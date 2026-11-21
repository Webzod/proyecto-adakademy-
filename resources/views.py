from datetime import timedelta
import logging
from pathlib import PurePosixPath
import re
import unicodedata

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import F, Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.http import url_has_allowed_host_and_scheme

<<<<<<< HEAD
from .forms import RecursoAcademicoForm
=======
from .forms import ComentarioForm
>>>>>>> feature/mejoras
from .models import RecursoAcademico


logger = logging.getLogger(__name__)
VIEW_COUNT_WINDOW_SECONDS = 30 * 60
VIEW_SESSION_KEY = "resource_views"
FAVORITES_SESSION_KEY = "favorite_resources"
COMMENT_SESSION_KEY = "resource_comments"
MAX_COMMENTS_PER_WINDOW = 5
COMMENT_WINDOW_SECONDS = 60
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


def normalize_search_text(value):
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(character for character in text if not unicodedata.combining(character))
    return " ".join(text.casefold().split())


def tokenize_search_text(value):
    return re.findall(r"\w+", normalize_search_text(value), flags=re.UNICODE)


def search_word_variants(word):
    variants = {word}
    if word.endswith("s"):
        variants.add(word[:-1])
    if word.endswith("es"):
        variants.add(word[:-2])
    return {variant for variant in variants if variant}


def search_word_matches(query_word, resource_words):
    variants = search_word_variants(query_word)
    for resource_word in resource_words:
        resource_variants = search_word_variants(resource_word)
        if variants.intersection(resource_variants):
            return True
        if any(
            len(variant) >= 3 and resource_word.startswith(variant)
            for variant in variants
        ):
            return True
    return False


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
        query_words = tokenize_search_text(query)
        matching_ids = []
        for recurso in recursos:
            searchable_text = normalize_search_text(
                " ".join(
                    (
                        recurso.titulo,
                        recurso.descripcion,
                        recurso.materia.nombre,
                        recurso.materia.facultad,
                        recurso.materia.semestre,
                        recurso.get_tipo_display(),
                        recurso.tipo,
                        recurso.archivo.name,
                    )
                )
            )
            searchable_words = tokenize_search_text(searchable_text)
            if all(
                search_word_matches(word, searchable_words)
                for word in query_words
            ):
                matching_ids.append(recurso.pk)
        recursos = recursos.filter(pk__in=matching_ids)
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
    request.session["resource_index_url"] = request.get_full_path()

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
            comment_times = request.session.get(COMMENT_SESSION_KEY, [])
            cutoff = now - timedelta(seconds=COMMENT_WINDOW_SECONDS)
            recent_comments = []
            for timestamp in comment_times if isinstance(comment_times, list) else []:
                parsed = parse_datetime(timestamp)
                if parsed is not None and timezone.is_aware(parsed) and parsed >= cutoff:
                    recent_comments.append(timestamp)
            if len(recent_comments) >= MAX_COMMENTS_PER_WINDOW:
                form.add_error(
                    "texto",
                    "Has publicado varios comentarios muy rápido. Espera un minuto e inténtalo de nuevo.",
                )
            else:
                comentario = form.save(commit=False)
                comentario.recurso = recurso
                comentario.save()
                recent_comments.append(now.isoformat())
                request.session[COMMENT_SESSION_KEY] = recent_comments
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
            "back_url": request.session.get("resource_index_url", "/"),
        },
    )


<<<<<<< HEAD
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
=======
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
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect("resources:detail", pk=recurso.pk)
>>>>>>> feature/mejoras


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
