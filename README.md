# SGMR — Sistema de Gestión de Mantenimiento de Racks

Aplicación web **móvil-first** para técnicos de refrigeración: registro en tiempo real de mantenimientos, trazabilidad y cálculo de MTTR.

## Requisitos

- Python 3.10+
- PostgreSQL (Supabase recomendado)
- Navegador con soporte de cámara (HTTPS en producción)

## Instalación

```bash
cd sgmr
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate   # Linux/macOS
pip install -r requirements.txt
cp .env.example .env
# Editar .env con SECRET_KEY y DATABASE_URL (Supabase)
```

## Base de datos

```bash
python manage.py migrate
python manage.py createsuperuser
```

Crear al menos una **Tienda** y un **Rack** con `id_qr` único en el admin (`/admin/`). El QR del rack debe contener ese `id_qr` (texto plano o URL con el ID).

## Ejecución local

```bash
python manage.py runserver
```

- Login: http://127.0.0.1:8000/
- Escáner: tras login se redirige a `/scanner/`
- Reportes: `/reportes/`

## Despliegue en Render

1. Repositorio en GitHub con este proyecto.
2. En Render: New → Web Service, conectar el repo.
3. Variables de entorno: `SECRET_KEY`, `DATABASE_URL` (Supabase), `DEBUG=False`, `ALLOWED_HOSTS=.onrender.com`.
4. Build: `pip install -r requirements.txt`
5. Start: `gunicorn config.wsgi`
6. La cámara en móvil requiere **HTTPS**; Render lo proporciona.

## Estructura de apps

| App        | Uso                                              |
|-----------|---------------------------------------------------|
| `users`   | Perfiles (Técnico/Supervisor), login, solo activos |
| `inventory` | Racks, tiendas, API por ID QR                    |
| `operations` | Cronómetro, check-in/check-out, bitácora        |
| `analytics`  | Reportes y MTTR                                 |

## Flujo del técnico

1. **Login** → solo técnicos activos.
2. **Escanear QR** del rack (cámara).
3. **Ficha técnica** → elegir Preventivo / Correctivo / Emergencia → inicia cronómetro.
4. **Parámetros de entrada** (presiones, temperaturas, set-points, amperajes).
5. **Cierre**: observaciones + parámetros finales → **Finalizar** (graba `hora_fin`, bloquea registro).

Si el técnico tiene una tarea abierta en otro rack, no puede iniciar otra hasta cerrarla.

## Licencia

Uso interno.
