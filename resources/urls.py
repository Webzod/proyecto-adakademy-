from django.urls import path

from . import views


app_name = "resources"

urlpatterns = [
    path("", views.index, name="index"),
    path("recurso/nuevo/", views.resource_create, name="create"),
    path("recurso/<int:pk>/", views.detail, name="detail"),
    path("recurso/<int:pk>/editar/", views.resource_update, name="update"),
    path("recurso/<int:pk>/eliminar/", views.resource_delete, name="delete"),
    path("recurso/<int:pk>/favorito/", views.toggle_favorite, name="favorite"),
    path("recurso/<int:pk>/descargar/", views.download, name="download"),
]
