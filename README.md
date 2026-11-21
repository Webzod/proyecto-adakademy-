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
Producción requiere PostgreSQL, una clave secreta y un directorio de media
montado en almacenamiento persistente. Instala `requirements.txt` en el entorno
del servidor y aplica las migraciones antes de iniciar la aplicación.

```powershell
$env:DJANGO_SECRET_KEY = (& .\venv\Scripts\python.exe -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
$env:DJANGO_DEBUG = "False"
$env:DJANGO_ALLOWED_HOSTS = "aula.ejemplo.edu"
$env:DJANGO_CSRF_TRUSTED_ORIGINS = "https://aula.ejemplo.edu"
$env:DJANGO_SECURE_SSL_REDIRECT = "True"
$env:DJANGO_DB_ENGINE = "django.db.backends.postgresql"
$env:DJANGO_DB_NAME = "aula_abierta"
$env:DJANGO_DB_USER = "aula_app"
$env:DJANGO_DB_PASSWORD = "<secreto-del-servidor>"
$env:DJANGO_DB_HOST = "postgres.ejemplo.internal"
$env:DJANGO_DB_PORT = "5432"
$env:DJANGO_DB_SSLMODE = "verify-full"
$env:DJANGO_MEDIA_ROOT = "E:\aula-abierta-data\media"
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check --deploy
```

En producción, sirve los estáticos recopilados en `staticfiles/` y los archivos
subidos en `DJANGO_MEDIA_ROOT` mediante el servidor web o almacenamiento
dedicado, detrás de HTTPS. El volumen que respalda `DJANGO_MEDIA_ROOT` debe ser
persistente, tener permisos de lectura/escritura para el proceso Django e
incluirse en la estrategia de copias de seguridad. Usa un usuario de base de
datos con permisos limitados, guarda las credenciales en el gestor de secretos
del servidor y configura el proxy para establecer `X-Forwarded-Proto` solo
cuando la solicitud original use HTTPS. `runserver` solo está destinado al
desarrollo.

Para mover los datos existentes desde SQLite, exporta los registros antes de
desplegar (`python manage.py dumpdata resources --indent 2 > resources.json`),
copia el contenido de `media/` al volumen persistente y cárgalos en PostgreSQL
después de migrar (`python manage.py loaddata resources.json`). Protege y elimina
el archivo de exportación una vez completada la migración.

## Validaciones

```powershell
python manage.py check
python manage.py test resources
python manage.py makemigrations --check --dry-run
npm run build:css
```
