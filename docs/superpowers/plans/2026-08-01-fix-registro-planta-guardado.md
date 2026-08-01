# Fix RegistroPlanta Guardado Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corregir `RegistroPlanta.marcar_cerrado()` para que persista todos los parámetros de la revisión de planta, no solo `cerrado` y `hora_fin`.

**Architecture:** Un fix de 1 línea en `inventory/models.py` replicando el patrón de `RegistroActividad.marcar_cerrado()` (usa `self.save()` completo). Se añade infraestructura de tests Django (no existe ninguna en el proyecto) usando SQLite para no tocar la BD de Supabase, más un test TDD que verifica persistencia completa de campos.

**Tech Stack:** Django 5.2.11, Python 3.13 (venv en `C:\Users\Usuario\first\venv`), test runner nativo de Django (`manage.py test`), SQLite en memoria para tests.

## Global Constraints

- BD de producción es Supabase PostgreSQL; **jamás** ejecutar `manage.py test` con el settings por defecto (intentaría crear `test_postgres` sin permiso). Siempre usar `--settings=config.test_settings`.
- Usar el venv del proyecto: `C:\Users\Usuario\first\venv\Scripts\python.exe`.
- No modificar el modelo de datos ni crear migraciones.
- Sin comentarios en el código nuevo salvo que sean necesarios.
- Repositorio: `C:\Users\Usuario\first`, rama `main`, worktree limpio al inicio.
- Los registros de planta vacíos ya existentes en producción se borrarán manualmente (fuera del alcance del código).

---

### Task 1: Infraestructura de test + test que falla (TDD red)

**Files:**
- Create: `config/test_settings.py`
- Create: `inventory/tests.py`
- Test: `inventory/tests.py`

**Interfaces:**
- Produces: `config/test_settings.py` (settings module para `manage.py test --settings=config.test_settings`); `inventory/tests.py` con `RegistroPlantaMarcarCerradoTest`.
- Consumes: modelos existentes `Tienda`, `PlantaElectrica`, `RegistroPlanta` (inventory/models.py), `get_user_model()` (users/models.py).

- [ ] **Step 1: Crear `config/test_settings.py`**

```python
from config.settings import *  # noqa: F401,F403

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}
```

- [ ] **Step 2: Crear `inventory/tests.py` con el test que falla**

```python
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from inventory.models import PlantaElectrica, RegistroPlanta, Tienda


class RegistroPlantaMarcarCerradoTest(TestCase):
    def setUp(self):
        tienda = Tienda.objects.create(nombre='Tienda Test')
        self.planta = PlantaElectrica.objects.create(
            id_qr='PLANTA-TEST-001',
            tienda=tienda,
            marca='Caterpillar',
        )
        self.tecnico = get_user_model().objects.create_user(
            username='tecnico1', password='testpass123'
        )

    def test_marcar_cerrado_persiste_todos_los_parametros(self):
        registro = RegistroPlanta.objects.create(
            planta=self.planta,
            tecnico=self.tecnico,
            fecha=timezone.now().date(),
        )
        registro.bateria_cantidad = 2
        registro.bateria_modelo = '12V 100Ah'
        registro.voltaje_l1l2 = Decimal('380.00')
        registro.amperaje_a1 = Decimal('10.50')
        registro.observaciones = 'Prueba persistencia'
        registro.marcar_cerrado()

        recargado = RegistroPlanta.objects.get(pk=registro.pk)
        self.assertTrue(recargado.cerrado)
        self.assertEqual(recargado.bateria_cantidad, 2)
        self.assertEqual(recargado.bateria_modelo, '12V 100Ah')
        self.assertEqual(recargado.voltaje_l1l2, Decimal('380.00'))
        self.assertEqual(recargado.amperaje_a1, Decimal('10.50'))
        self.assertEqual(recargado.observaciones, 'Prueba persistencia')
```

- [ ] **Step 3: Ejecutar el test para verificar que FALLA**

Run:
```bash
& "C:\Users\Usuario\first\venv\Scripts\python.exe" "C:\Users\Usuario\first\manage.py" test inventory --settings=config.test_settings --verbosity=2
```
Expected: FAIL. El test runner arranca, migra a SQLite, y falla en la primera `assertEqual(recargado.bateria_cantidad, 2)` porque `marcar_cerrado()` solo persiste `cerrado`/`hora_fin` (el resto queda `None` al re-leer de BD).

- [ ] **Step 4: Commit**

```bash
git add config/test_settings.py inventory/tests.py
git commit -m "test: add failing test for RegistroPlanta.marcar_cerrado persistence"
```

---

### Task 2: Implementar el fix (TDD green)

**Files:**
- Modify: `inventory/models.py:180-182` (método `marcar_cerrado` de `RegistroPlanta`)
- Test: `inventory/tests.py`

**Interfaces:**
- Consumes: test `test_marcar_cerrado_persiste_todos_los_parametros` de Task 1.
- Produces: `RegistroPlanta.marcar_cerrado()` con firma idéntica (`self.cerrado = True; self.save()`), sin romper `hora_fin` (se sigue asignando en la vista antes de llamar).

- [ ] **Step 1: Cambiar `marcar_cerrado` en `inventory/models.py:180-182`**

Antes:
```python
    def marcar_cerrado(self):
        self.cerrado = True
        self.save(update_fields=['cerrado', 'hora_fin'])
```

Después:
```python
    def marcar_cerrado(self):
        self.cerrado = True
        self.save()
```

- [ ] **Step 2: Ejecutar el test para verificar que PASA**

Run:
```bash
& "C:\Users\Usuario\first\venv\Scripts\python.exe" "C:\Users\Usuario\first\manage.py" test inventory --settings=config.test_settings --verbosity=2
```
Expected: PASS (1 test).

- [ ] **Step 3: Commit**

```bash
git add inventory/models.py
git commit -m "fix: persist all RegistroPlanta fields on marcar_cerrado"
```

---

### Task 3: Verificación del flujo completo

**Files:**
- Test: `inventory/tests.py`, `operations` (sin tests propios; se verifica que todo el suite carga y corre)

**Interfaces:**
- Consumes: settings de test de Task 1, fix de Task 2.

- [ ] **Step 1: Correr el suite completo de tests con SQLite**

Run:
```bash
& "C:\Users\Usuario\first\venv\Scripts\python.exe" "C:\Users\Usuario\first\manage.py" test --settings=config.test_settings --verbosity=1
```
Expected: OK, 1 test ejecutado, 0 fallos. (Confirma que las apps `users`, `inventory`, `operations`, `analytics` migran y arrancan bien en SQLite.)

- [ ] **Step 2: Confirmar que no se requiere migración de datos**

Run:
```bash
& "C:\Users\Usuario\first\venv\Scripts\python.exe" "C:\Users\Usuario\first\manage.py" makemigrations --check --dry-run --settings=config.test_settings
```
Expected: `No changes detected` (el fix no altera el esquema).

- [ ] **Step 3: Actualizar estado del plan y commit final**

Marcar los 2 primeros tasks como completados en este documento si aún no lo están, y:

```bash
git add docs/superpowers/plans/2026-08-01-fix-registro-planta-guardado.md
git commit -m "docs: mark fix registro planta plan as executed"
```
