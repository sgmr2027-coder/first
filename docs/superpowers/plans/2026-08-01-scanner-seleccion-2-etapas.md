# Scanner 2 Etapas (Tienda → Equipo) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rediseñar el escáner para que el técnico seleccione primero la tienda y luego el equipo (rack/planta), reemplazando los dos `<select>` planos actuales.

**Architecture:** El contexto de `ScannerView` agrega `tiendas` (para el dropdown 1) y listas JSON serializables de racks/plantas (para el dropdown 2). El template embebe esos JSON con `json_script` y un script filtra en el cliente sin llamadas extra al servidor. El flujo Continuar → `buscarEquipo()` → API QR → ficha queda intacto.

**Tech Stack:** Django 5.2, Bootstrap 5.3.2 (ya en `base.html`), JS vanilla, `json_script` filter de Django, test runner de Django con `config/test_settings.py`.

## Global Constraints

- No cambiar BD, modelos, migraciones, URLs, dashboard, check-in/checkout ni PDFs.
- BD de producción es Supabase PostgreSQL: **jamás** correr `manage.py test` sin `--settings=config.test_settings`.
- Comando de tests: `& C:\Users\Usuario\first\venv\Scripts\python.exe manage.py test operations --settings=config.test_settings` (ajustar ruta del worktree).
- `config/test_settings.py` no existe en main (el Bug #1 no está mergeado); hay que crearlo de nuevo en este worktree.
- El valor del `<option>` del dropdown 2 debe ser `id_qr` (el JS actual lo usa para el API QR).
- Sin comentarios en código nuevo salvo los ya existentes en el patrón.

---

### Task 1: Infraestructura de test (test_settings.py + test de vista)

**Files:**
- Create: `config/test_settings.py`
- Create: `operations/tests.py`
- Test: `operations/tests.py`

**Interfaces:**
- Produces: `config.test_settings` (override SQLite in-memory) y `ScannerViewTest` con un técnico autenticado reutilizable.

- [ ] **Step 1: Create `config/test_settings.py`**

```python
from config.settings import *  # noqa: F401,F403

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}
```

- [ ] **Step 2: Write the failing test**

```python
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from inventory.models import PlantaElectrica, Rack, Tienda
from users.models import Rol


class ScannerViewTest(TestCase):
    def setUp(self):
        tienda_a = Tienda.objects.create(nombre='Tienda A')
        Tienda.objects.create(nombre='Tienda B')
        self.rack = Rack.objects.create(id_qr='RACK-001', tienda=tienda_a, activo=True)
        self.planta = PlantaElectrica.objects.create(id_qr='PLANTA-001', tienda=tienda_a, activo=True)
        self.tecnico = get_user_model().objects.create_user(
            username='tecnico1', password='testpass123', rol=Rol.TECNICO
        )

    def test_scanner_requiere_login(self):
        resp = self.client.get(reverse('operations:scanner'))
        self.assertEqual(resp.status_code, 302)

    def test_scanner_redirige_supervisor_al_dashboard(self):
        supervisor = get_user_model().objects.create_user(
            username='super1', password='testpass123', rol=Rol.SUPERVISOR
        )
        self.client.login(username='super1', password='testpass123')
        resp = self.client.get(reverse('operations:scanner'))
        self.assertRedirects(resp, reverse('analytics:dashboard'))

    def test_scanner_contexto_incluye_tiendas_y_datos_json(self):
        self.client.login(username='tecnico1', password='testpass123')
        resp = self.client.get(reverse('operations:scanner'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('tiendas', resp.context)
        self.assertIn('racks_data', resp.context)
        self.assertIn('plantas_data', resp.context)
        self.assertEqual(
            resp.context['racks_data'],
            [{'id_qr': 'RACK-001', 'tienda__nombre': 'Tienda A', 'ubicacion': ''}],
        )
        self.assertEqual(
            resp.context['plantas_data'],
            [{'id_qr': 'PLANTA-001', 'tienda__nombre': 'Tienda A', 'ubicacion': ''}],
        )
```

- [ ] **Step 3: Run test to verify it fails**

Run: `& <venv>\python.exe manage.py test operations --settings=config.test_settings`
Expected: `AttributeError: 'ScannerViewTest' object has no attribute 'client'` o `No such table` — el test no pasa porque `operations/tests.py` no existe o el contexto no tiene los campos.

- [ ] **Step 4: Commit**

```bash
git add config/test_settings.py operations/tests.py
git commit -m "test: infra de tests y test de contexto del scanner"
```

---

### Task 2: Ampliar ScannerView (tiendas + datos JSON)

**Files:**
- Modify: `operations/views.py:16` (import de `Tienda`)
- Modify: `operations/views.py:32-40` (`ScannerView.get`)

**Interfaces:**
- Consumes: contexto `tiendas` (queryset de `Tienda`), `racks_data`, `plantas_data` (listas de dicts).
- Produces: claves de contexto `tiendas`, `racks_data`, `plantas_data` que consume el template (Task 3).

- [ ] **Step 1: Add `Tienda` to the import**

Modify line 16:

```python
from inventory.models import Rack, PlantaElectrica, RegistroPlanta, Tienda
```

- [ ] **Step 2: Extend `ScannerView.get`**

Replace the current `get` method body:

```python
    def get(self, request):
        tarea_abierta = obtener_tarea_abierta(request.user)
        racks_qs = Rack.objects.filter(activo=True).select_related('tienda').order_by('tienda__nombre', 'ubicacion')
        plantas_qs = PlantaElectrica.objects.filter(activo=True).select_related('tienda').order_by('tienda__nombre', 'ubicacion')
        return render(request, 'operations/scanner.html', {
            'tarea_abierta': tarea_abierta,
            'tiendas': Tienda.objects.all(),
            'racks': racks_qs,
            'plantas': plantas_qs,
            'racks_data': list(racks_qs.values('id_qr', 'tienda__nombre', 'ubicacion')),
            'plantas_data': list(plantas_qs.values('id_qr', 'tienda__nombre', 'ubicacion')),
        })
```

- [ ] **Step 3: Run test to verify it passes**

Run: `& <venv>\python.exe manage.py test operations --settings=config.test_settings`
Expected: 3 tests PASS. (Los que verifican login/redirect ya pasaban; el de contexto pasa ahora.)

- [ ] **Step 4: Commit**

```bash
git add operations/views.py
git commit -m "feat: agregar tiendas y datos JSON al contexto del scanner"
```

---

### Task 3: Rediseñar scanner.html (dropdown 1 tienda + dropdown 2 equipo)

**Files:**
- Modify: `templates/operations/scanner.html:42-60` (reemplazar los dos `<select>` por el esquema 2 etapas)
- Modify: `templates/operations/scanner.html:73-155` (bloque `extra_js`)

**Interfaces:**
- Consumes: contexto `tiendas`, `racks`, `plantas`, `racks_data`, `plantas_data` (Task 2).

- [ ] **Step 1: Replace the two selects with the 2-stage UI**

Replace lines 42-60 (the `#container_rack` and `#container_planta` divs) with:

```html
        <div class="mb-4">
          <label class="form-label text-muted small fw-bold" for="select_tienda">TIENDA</label>
          <select class="form-select form-select-lg" id="select_tienda">
            <option value="">— Seleccionar tienda —</option>
            {% for tienda in tiendas %}
              <option value="{{ tienda.nombre }}">{{ tienda.nombre }}</option>
            {% endfor %}
          </select>
        </div>

        <div class="mb-4">
          <label class="form-label text-muted small fw-bold" for="select_equipo">EQUIPO</label>
          <select class="form-select form-select-lg" id="select_equipo" disabled>
            <option value="">— Seleccionar —</option>
          </select>
          <div id="sin_equipos" class="d-none text-center text-muted small mt-2">
            <i class="bi bi-info-circle me-1"></i>Sin equipos activos
          </div>
        </div>
```

- [ ] **Step 2: Add the JSON data blocks before the JS script**

At the end of `{% block content %}` (after the `</div>` that closes `.card-body`, i.e. before `{% endblock %}`):

```html
{{ racks_data|json_script:"racks-data" }}
{{ plantas_data|json_script:"plantas-data" }}
```

- [ ] **Step 3: Replace the JS in `extra_js`**

Replace the whole `<script>...</script>` content (lines 75-153) with:

```javascript
(function () {
  const URLS = {
    "api_rack":    "{% url 'operations:api_rack_qr'   id_qr='__ID__' %}",
    "api_planta":  "{% url 'operations:api_planta_qr' id_qr='__ID__' %}",
    "ficha_rack":  "{% url 'operations:ficha'         rack_id=999999 %}",
    "ficha_planta": "{% url 'operations:ficha_planta' planta_id=999999 %}"
  };

  const racksData   = JSON.parse(document.getElementById('racks-data').textContent);
  const plantasData = JSON.parse(document.getElementById('plantas-data').textContent);

  const btnRack      = document.getElementById('btn_rack');
  const btnPlanta    = document.getElementById('btn_planta');
  const selectTienda = document.getElementById('select_tienda');
  const selectEquipo = document.getElementById('select_equipo');
  const sinEquipos   = document.getElementById('sin_equipos');
  const btnContinuar = document.getElementById('btn_continuar');
  const resultado    = document.getElementById('resultado');

  let esRack = true;
  let procesando = false;

  function poblarEquipos() {
    const tienda = selectTienda.value;
    const fuente = esRack ? racksData : plantasData;
    const filtrados = tienda ? fuente.filter(function (e) { return e.tienda__nombre === tienda; }) : [];

    selectEquipo.innerHTML = '<option value="">— Seleccionar —</option>';
    filtrados.forEach(function (e) {
      const opt = document.createElement('option');
      opt.value = e.id_qr;
      opt.textContent = (e.ubicacion ? e.ubicacion + ' — ' : '') + e.id_qr;
      selectEquipo.appendChild(opt);
    });

    selectEquipo.disabled = !tienda;
    sinEquipos.classList.toggle('d-none', filtrados.length > 0);
    resultado.innerHTML = '';
  }

  btnRack.addEventListener('change', function () { esRack = true; poblarEquipos(); });
  btnPlanta.addEventListener('change', function () { esRack = false; poblarEquipos(); });
  selectTienda.addEventListener('change', poblarEquipos);

  poblarEquipos();

  function buscarEquipo(idQr) {
    if (!idQr || procesando) return;
    procesando = true;
    btnContinuar.disabled = true;

    const etiqueta = esRack ? 'Rack' : 'Planta';
    resultado.innerHTML = '<div class="alert alert-light border small text-center text-muted"><i class="bi bi-search me-2"></i>Verificando ' + etiqueta + '...</div>';

    const apiUrl = (esRack ? URLS.api_rack : URLS.api_planta).replace('__ID__', encodeURIComponent(idQr));

    fetch(apiUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(r => {
        if (!r.ok) {
          return r.json().then(data => { throw new Error(data.error || 'Error HTTP ' + r.status); })
                        .catch(() => { throw new Error('Error de conexión con el servidor.'); });
        }
        return r.json();
      })
      .then(data => {
        if (data.ok) {
          resultado.innerHTML = '<div class="alert alert-success border-0 small text-center"><i class="bi bi-check-circle-fill me-2"></i>Equipo verificado. Accediendo...</div>';
          const url = esRack
            ? URLS.ficha_rack.replace('999999', data.id)
            : URLS.ficha_planta.replace('999999', data.id);
          window.location.href = url;
        } else {
          throw new Error(data.error || 'Equipo no encontrado.');
        }
      })
      .catch(err => {
        resultado.innerHTML = '<div class="alert alert-danger border-0 small text-center"><i class="bi bi-exclamation-triangle-fill me-2"></i>' + err.message + '</div>';
        procesando = false;
        btnContinuar.disabled = false;
      });
  }

  btnContinuar.addEventListener('click', function () {
    const idQr = selectEquipo.value;
    if (!idQr) {
      resultado.innerHTML = '<div class="alert alert-secondary border-0 small text-center"><i class="bi bi-info-circle me-2"></i>Seleccione un equipo del listado para continuar.</div>';
      return;
    }
    buscarEquipo(idQr);
  });
})();
```

- [ ] **Step 4: Run the test suite to confirm nothing broke**

Run: `& <venv>\python.exe manage.py test operations --settings=config.test_settings`
Expected: 3 tests PASS.

- [ ] **Step 5: Verify no DB drift**

Run: `& <venv>\python.exe manage.py makemigrations --check --settings=config.test_settings`
Expected: `No changes detected`

- [ ] **Step 6: Manual smoke check**

Run the server (`& <venv>\python.exe manage.py runserver --settings=config.test_settings`) and open `/operations/scanner/` with a técnico. Confirm:
- Dropdown 1 lista todas las tiendas.
- Al elegir tienda + tipo, dropdown 2 se llena solo con equipos de esa tienda.
- Tienda sin equipos de un tipo muestra "Sin equipos activos" y dropdown 2 sin opciones.
- Continuar con un equipo redirige a su ficha.

- [ ] **Step 7: Commit**

```bash
git add templates/operations/scanner.html
git commit -m "feat: escáner con selección de tienda y equipo en 2 etapas"
```

---

## Self-Review

- **Spec coverage:** tiendas (Task 2/3), dropdown 2 filtrado + "Sin equipos activos" (Task 3), sin cambios BD/URLs/dashboard (solo se tocan `views.py` y `scanner.html`), test de contexto (Task 1/2). ✓
- **Placeholder scan:** todas las claves (`racks_data`, `plantas_data`, `tienda__nombre`, `id_qr`, `ubicacion`) coinciden entre vista, template y test. ✓
- **Type consistency:** `tienda__nombre` viene de `values('tienda__nombre')` y se lee igual en el filtro JS y en el test. `id_qr` y `ubicacion` coinciden en ambos. ✓
