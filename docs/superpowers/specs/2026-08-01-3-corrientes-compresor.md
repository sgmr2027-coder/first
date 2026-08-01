# Bug #3: 3 corrientes (Amp 1/2/3) por compresor — racks trifásicos

Fecha: 2026-08-01
Estado: Aprobado

## Síntoma

En los racks de refrigeración, cada compresor es trifásico y debería registrar 3 corrientes (una por fase). Hoy los formularios de check-in y check-out solo capturan **una** corriente por compresor (`corriente_compresor_{i}`), y el PDF de la intervención muestra columnas vacías porque la plantilla renderiza una clave inexistente.

## Causa raíz

- `ParametrosEntradaForm` y `ParametrosSalidaForm` (`operations/forms.py`) generan 1 campo por compresor: `corriente_compresor_{i}`.
- El PDF (`IntervencionPDFView`, `operations/views.py:366-368`) ya fue diseñado esperando 3 claves por compresor (`corriente1_compresor_{i}`, `corriente2_compresor_{i}`, `corriente3_compresor_{i}`), pero los formularios nunca las generan → en el PDF salen "—".
- `reporte_pdf.html:331` renderiza `{{ c.corriente }}`, clave que no existe en el contexto del PDF (el contexto usa `corriente_1/2/3`) → columna "Corriente" siempre vacía.

## Decisión de diseño

**Opción A (aprobada):** Generar 3 campos numéricos por compresor en los formularios de check-in y check-out:

- Claves: `corriente1_compresor_{i}`, `corriente2_compresor_{i}`, `corriente3_compresor_{i}`.
- Etiquetas: "Amp 1", "Amp 2", "Amp 3" (con sufijo "(media)"/"(baja)" según el grupo del compresor).
- Coincide con la estructura que el PDF ya espera.
- Los datos se guardan en el JSON existente `datos_entrada`/`datos_salida` — sin cambios de modelos ni migraciones.

**Fallback histórico:** En el PDF, si `corriente1_compresor_{i}` no existe pero sí `corriente_compresor_{i}` (registros antiguos con 1 sola corriente), usar ese valor en `corriente_1`.

Rechazadas:
- **B:** Un campo de texto libre "A1 / A2 / A3" — UX pobre y sin validación numérica por fase.
- **C:** Modelo separado de medición por compresor — sobre-ingeniería; rompe la consistencia del diseño JSON actual.

## Alcance

- `operations/forms.py`: `_corriente_field` → 3 campos por compresor; `get_compresores()` de ambos formularios devuelve `corriente_1/2/3`.
- `templates/operations/checkin.html`: columna única → 3 columnas "Amp 1/2/3".
- `templates/operations/checkout.html`: columna única → 3 columnas "Amp 1/2/3".
- `operations/views.py`: fallback histórico en `IntervencionPDFView`.
- `templates/operations/reporte_pdf.html`: columna "Corriente" → 3 columnas "Amp 1/2/3" (corrige bug de columna vacía).
- Sin cambios de modelos, BD, migraciones, URLs ni scanner.

## Datos existentes

Los registros históricos (una sola `corriente_compresor_{i}`) siguen siendo legibles gracias al fallback en el PDF. No hay migración de datos.

## Verificación

- `python manage.py test operations --settings=config.test_settings` debe pasar.
- Test nuevo: los formularios generan 3 campos por compresor; fallback del PDF con datos históricos.
- Revisión visual de check-in, check-out y PDF (3 columnas por compresor).
