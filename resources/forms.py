from django import forms

from .models import Comentario


class ComentarioForm(forms.ModelForm):
    class Meta:
        model = Comentario
        fields = ("texto",)
        widgets = {
            "texto": forms.Textarea(
                attrs={
                    "class": "form-input form-textarea",
                    "placeholder": "Comparte una duda o una explicación útil...",
                    "rows": 4,
                }
            ),
        }
        labels = {"texto": "Tu comentario"}

