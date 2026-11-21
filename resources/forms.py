from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Comentario, RecursoAcademico


class RegistroForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username",)
        widgets = {
            "username": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "autocomplete": "username",
                    "autofocus": True,
                    "placeholder": "Elige un nombre de usuario",
                }
            ),
        }
        labels = {"username": "Nombre de usuario"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].widget.attrs.update(
            {
                "class": "form-input",
                "autocomplete": "new-password",
                "placeholder": "Crea una contraseña segura",
            }
        )
        self.fields["password2"].widget.attrs.update(
            {
                "class": "form-input",
                "autocomplete": "new-password",
                "placeholder": "Escribe de nuevo tu contraseña",
            }
        )
        self.fields["password1"].label = "Contraseña"
        self.fields["password2"].label = "Confirmar contraseña"


class RecursoAcademicoForm(forms.ModelForm):
    class Meta:
        model = RecursoAcademico
        fields = ("titulo", "descripcion", "tipo", "materia", "archivo")
        widgets = {
            "titulo": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Ej. Guía de cálculo diferencial",
                    "autocomplete": "off",
                }
            ),
            "descripcion": forms.Textarea(
                attrs={
                    "class": "form-input form-textarea",
                    "placeholder": "Describe qué encontrará otro estudiante...",
                    "rows": 5,
                }
            ),
            "tipo": forms.Select(attrs={"class": "form-input"}),
            "materia": forms.Select(attrs={"class": "form-input"}),
            "archivo": forms.FileInput(attrs={"class": "form-input form-file"}),
        }
        labels = {
            "titulo": "Título del recurso",
            "descripcion": "Descripción",
            "tipo": "Tipo de material",
            "materia": "Materia",
            "archivo": "Archivo",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["materia"].queryset = self.fields["materia"].queryset.order_by(
            "nombre"
        )
        self.fields["archivo"].help_text = (
            "PDF, Office, CSV, texto o imagen. Tamaño máximo: 25 MB."
        )
        if self.instance and self.instance.pk:
            self.fields["archivo"].required = False
            self.fields["archivo"].help_text = (
                "El archivo actual se conserva si no seleccionas uno nuevo."
            )


class ComentarioForm(forms.ModelForm):
    def clean_texto(self):
        texto = self.cleaned_data["texto"].strip()
        if not texto:
            raise forms.ValidationError("El comentario no puede estar vacío.")
        return texto

    class Meta:
        model = Comentario
        fields = ("texto",)
        widgets = {
            "texto": forms.Textarea(
                attrs={
                    "class": "form-input form-textarea",
                    "placeholder": "Comparte una duda o una explicación útil...",
                    "rows": 4,
                    "maxlength": 2000,
                }
            ),
        }
        labels = {"texto": "Tu comentario"}
