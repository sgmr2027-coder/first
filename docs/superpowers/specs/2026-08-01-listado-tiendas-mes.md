# Bug #4: Listado de tiendas intervenidas en el mes (técnico)

Fecha: 2026-08-01
Estado: Aprobado

## Síntoma

Los técnicos no tienen forma de ver, al inicio de su sesión, en qué tiendas han trabajado durante el mes. El escáner solo permite elegir equipo para una nueva intervención; no hay visibilidad del historial mensual de tiendas.

## Requisitos (acordados)

- Botón en el menú superior (junto a "Inicio", solo técnicos) que lleve al listado de tiendas intervenidas en el mes actual.
- El técnico sigue aterrizando en el escáner al iniciar sesión (`LOGIN_REDIRECT_URL` no cambia).
- El listado muestra **una fila por intervención cerrada del mes**: Tienda, tipo de equipo (Rack/Planta) y fecha.
- Sin enlaces a PDF ni a detalles.
- Solo el mes actual, para no saturar la página con todo el historial.
- Solo intervenciones cerradas (`cerrado=True`).

## Decisión de diseño

Nueva vista `MisIntervencionesView` en `operations/views.py` que combina dos consultas del mes actual para el técnico logueado:

- Racks: `RegistroActividad.objects.filter(tecnico=request.user, cerrado=True, hora_fin__range=(inicio_mes, inicio_sig_mes)).select_related('rack__tienda')`
- Plantas: `RegistroPlanta.objects.filter(tecnico=request.user, cerrado=True, hora_fin__range=(...)).select_related('planta__tienda')`

Ambas se unifican en una lista de dicts `{'tienda': nombre, 'tipo': 'Rack'|'Planta', 'fecha': ...}` ordenada por **fecha descendente**. Son solo 2 consultas livianas (filtradas por usuario y mes) — sin riesgo de saturar la BD.

## Alcance

- `operations/views.py`: nueva vista `MisIntervencionesView` (`TecnicoRequiredMixin`).
- `operations/urls.py`: `path('mis-intervenciones/', ..., name='mis_intervenciones')`.
- `templates/operations/mis_intervenciones.html`: tabla/card con columnas Tienda | Tipo | Fecha; botón "Ir al escáner"; mensaje vacío "No has intervenido tiendas este mes".
- `templates/base.html`: botón "Tiendas del mes" junto a "Inicio" (solo técnicos).
- `operations/tests.py`: tests de la vista.
- Sin cambios de modelos, BD, migraciones ni `LOGIN_REDIRECT_URL`.

## Verificación

- Test: técnico con 1 rack + 1 planta cerrados del mes → 200 y lista con ambos tipos y orden correcto.
- Test: técnico sin intervenciones → lista vacía.
- Test: supervisor → redirigido al dashboard.
- `python manage.py test operations --settings=config.test_settings` debe pasar.
- `python manage.py makemigrations --check --settings=config.test_settings`: `No changes detected`.
