# Bug #2: Scanner con selección en 2 etapas (tienda → equipo)

Fecha: 2026-08-01
Estado: Aprobado

## Síntoma

La pantalla de escáner (`operations/scanner.html`, vista `ScannerView`) presenta un listado plano de todos los racks y todas las plantas en dos `<select>` únicos. Con el volumen actual de equipos el listado es incómodo y ocupa toda la pantalla: el técnico debe leer una lista larga para encontrar el equipo correcto, y la lista crece con cada nueva tienda.

## Causa raíz

Diseño de UI: un solo dropdown por tipo de equipo mezcla todas las tiendas. No hay forma de estrechar la búsqueda por sucursal, y el listado se vuelve ilegible cuando hay muchas tiendas.

## Decisión de diseño

**Opción aprobada:** Selección en 2 etapas:

1. **Dropdown 1 — TIENDA:** lista de todas las tiendas (siempre visible, independiente del tipo de equipo). Las tiendas son las mismas para racks y plantas (todas tienen al menos 1 de cada), así que se renderiza estática en el HTML.
2. **Dropdown 2 — EQUIPO:** se llena por JavaScript según el tipo elegido (Rack/Planta) y la tienda seleccionada. Si la tienda no tiene equipos activos del tipo elegido, el dropdown queda vacío con un mensaje "Sin equipos activos".

Los datos de racks y plantas se embeben en el HTML como JSON (`json_script`) para filtrar en el cliente, sin llamadas extra al servidor. El flujo existente (botón Continuar → `buscarEquipo()` → API QR → redirigir a ficha) no cambia: solo cambia de dónde sale el `id_qr`.

## Alcance

- `operations/views.py` (`ScannerView`): agregar `tiendas` al contexto y datos JSON serializables de racks/plantas (con su tienda).
- `templates/operations/scanner.html`: reemplazar los dos `<select>` planos por el esquema 2 etapas con JS de filtrado.
- Sin cambios de BD, modelos, migraciones, URLs, dashboard, check-in/checkout ni PDFs.
- Test nuevo de vista: `ScannerView` requiere técnico, devuelve 200 y su contexto incluye `tiendas`, `racks`, `plantas` y los datos JSON.

## Datos existentes

No hay migración de datos. Las tiendas y equipos existentes ya se relacionan vía `Rack.tienda` y `PlantaElectrica.tienda` (`select_related`).

## Verificación

- `python manage.py test operations --settings=config.test_settings` debe pasar.
- `python manage.py makemigrations --check --settings=config.test_settings`: `No changes detected`.
- Revisión manual del escáner: filtrar por tienda y tipo; mensaje "Sin equipos activos" en tienda sin equipos del tipo.
