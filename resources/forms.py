from django import forms

from .models import Comentario


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

