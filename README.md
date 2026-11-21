# Aula Abierta

Plataforma Django de solo lectura para explorar guías de estudio, apuntes y
materiales de clase compartidos por materia, texto y tipo. La descripción de
cada recurso permite consultar qué incluye antes de descargarlo. La aplicación
no incorpora autenticación ni operaciones para crear, editar o eliminar recursos.

## Desarrollo local (PowerShell)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
npm install
npm run build:css
python manage.py migrate
python manage.py runserver
```

La hoja de estilos compilada se sirve desde `resources/static/resources/css/`;
vuelve a ejecutar `npm run build:css` cuando cambies plantillas, configuración
Tailwind o `resources/static_src/css/app.css`. Durante el desarrollo puedes
usar `npm run watch:css`.

Los archivos permitidos para recursos son PDF, documentos y hojas de cálculo
de Office, CSV, texto e imágenes PNG/JPG, con un tamaño máximo de 25 MB.

## Configuración de despliegue

Configura estas variables en el entorno del servidor. No habilites `DEBUG` en
producción y usa los dominios reales, separados por comas, en `DJANGO_ALLOWED_HOSTS`.

```powershell
$env:DJANGO_SECRET_KEY = (& .\venv\Scripts\python.exe -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
$env:DJANGO_DEBUG = "False"
$env:DJANGO_ALLOWED_HOSTS = "aula.ejemplo.edu"
$env:DJANGO_CSRF_TRUSTED_ORIGINS = "https://aula.ejemplo.edu"
$env:DJANGO_SECURE_SSL_REDIRECT = "True"
python manage.py collectstatic --noinput
```

En producción, sirve los estáticos recopilados en `staticfiles/` y los archivos
subidos en `media/` mediante el servidor web o almacenamiento dedicado, detrás
de HTTPS. `runserver` solo está destinado al desarrollo.

## Validaciones

```powershell
python manage.py check
python manage.py test resources
python manage.py makemigrations --check --dry-run
npm run build:css
```
