# Fix Bug #1: Revisión de planta no guarda parámetros en BD

Fecha: 2026-08-01
Estado: Aprobado

## Síntoma

Al crear una revisión mensual de una planta eléctrica (flujo `IniciarRevisionPlantaView` → `RevisionPlantaView`), la fila `RegistroPlanta` aparece en la BD con la fecha, pero ninguno de los parámetros capturados en el formulario se guarda. El PDF generado (`PlantaPDFView`) sale vacío porque lee los datos de la BD.

## Causa raíz

`RegistroPlanta.marcar_cerrado()` en `inventory/models.py` persiste solo dos campos:

```python
def marcar_cerrado(self):
    self.cerrado = True
    self.save(update_fields=['cerrado', 'hora_fin'])
```

La vista `RevisionPlantaView.post` asigna ~30 parámetros al objeto en memoria (`registro.bateria_cantidad`, `registro.voltaje_l1l2`, ...) y luego llama `marcar_cerrado()`. Como `save(update_fields=['cerrado', 'hora_fin'])` solo escribe esos 2 campos, todos los demás parámetros se descartan al persistir.

El flujo de Rack funciona porque `RegistroActividad.marcar_cerrado()` (operations/models.py) usa `self.save()` sin `update_fields`, que guarda todos los campos modificados.

El bug se introdujo en el commit `b988939` cuando se movieron los modelos de planta a `inventory/models.py`.

## Decisión de diseño

**Opción A (aprobada):** Cambiar `RegistroPlanta.marcar_cerrado()` para usar `self.save()` completo, replicando el patrón de `RegistroActividad`. Es el mínimo cambio y elimina la divergencia entre ambos modelos.

Rechazadas:
- **B:** Guardar explícito en la vista — deja el modelo con el bug latente.
- **C:** `update_fields` parametrizable — sobre-ingeniería para un fix de 1 línea.

## Alcance

- Cambio de 1 línea en `inventory/models.py` (método `marcar_cerrado`).
- Añadir infraestructura de tests Django (no existe ninguna en el proyecto) y un test que pruebe que `marcar_cerrado()` persiste todos los campos, no solo `cerrado`/`hora_fin`.

## Datos existentes

Los registros de planta vacíos que ya existen en la BD de producción se borrarán manualmente antes de desplegar; no se requiere migración de datos.

## Verificación

- `python manage.py test operations inventory` debe pasar (test nuevo + existentes).
- Test nuevo: crear `RegistroPlanta`, asignar varios campos, llamar `marcar_cerrado()`, re-leer desde BD y confirmar que todos los campos persistieron.
