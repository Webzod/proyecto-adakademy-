from django import forms

from .models import RecursoAcademico


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
