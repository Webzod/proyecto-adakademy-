from django.urls import path

from . import views


app_name = "resources"

urlpatterns = [
    path("", views.index, name="index"),
    path("recurso/<int:pk>/", views.detail, name="detail"),
    path("recurso/<int:pk>/descargar/", views.download, name="download"),
]
