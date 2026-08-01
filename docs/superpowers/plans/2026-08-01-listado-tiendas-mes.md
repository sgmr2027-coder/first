# Listado de Tiendas Intervenidas del Mes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mostrar al técnico, desde un botón del menú superior, el listado de tiendas intervenidas en el mes actual (una fila por intervención cerrada: tienda, tipo, fecha).

**Architecture:** Nueva vista `MisIntervencionesView` (operations/views.py) con `TecnicoRequiredMixin` que ejecuta 2 consultas (racks de `RegistroActividad` y plantas de `RegistroPlanta`, ambas `cerrado=True` y `hora_fin` dentro del mes actual, con `select_related`), unifica en una lista de dicts y la ordena por fecha descendente. Nueva URL `mis-intervenciones`, nueva plantilla, botón en el menú (base.html).

**Tech Stack:** Django 5.2, class-based views, `timezone.now()`, test runner con `config/test_settings.py`.

## Global Constraints

- No cambiar modelos, BD, migraciones ni `LOGIN_REDIRECT_URL` (sigue en `operations:scanner`).
- BD de producción es Supabase PostgreSQL: **jamás** correr `manage.py test` sin `--settings=config.test_settings`.
- Solo intervenciones `cerrado=True` del mes actual.
- Sin enlaces a PDF ni detalles; solo tienda, tipo y fecha.
- Comando de tests: `& C:\Users\Usuario\first\venv\Scripts\python.exe manage.py test operations --settings=config.test_settings`.
- Sin comentarios nuevos salvo los del patrón existente.

---

### Task 1: Vista `MisIntervencionesView` + URL + tests

**Files:**
- Modify: `operations/views.py` (agregar import de `RegistroPlanta` y la vista; el import actual de `inventory.models` ya incluye `Rack`, `PlantaElectrica`, `RegistroPlanta`, `Tienda`)
- Modify: `operations/urls.py`
- Modify: `operations/tests.py`
- Test: `operations/tests.py`

**Interfaces:**
- Produces: URL `operations:mis_intervenciones` y contexto `intervenciones` (lista de dicts `{'tienda', 'tipo', 'fecha'}` ordenada por fecha descendente) que consume la plantilla (Task 2).

- [ ] **Step 1: Write the failing tests**

Append to `operations/tests.py`:

```python
from operations.models import RegistroActividad, TipoActividad


class MisIntervencionesViewTest(TestCase):
    def setUp(self):
        self.tienda = Tienda.objects.create(nombre='Tienda A', codigo='A')
        self.rack = Rack.objects.create(id_qr='RACK-001', tienda=self.tienda, activo=True)
        self.planta = PlantaElectrica.objects.create(id_qr='PLANTA-001', tienda=self.tienda, activo=True)
        self.tecnico = get_user_model().objects.create_user(
            username='tecnico1', password='testpass123', rol=Rol.TECNICO
        )

    def _registro_rack(self, cerrado=True, dias_atras=1):
        from django.utils import timezone
        from datetime import timedelta
        ahora = timezone.now()
        return RegistroActividad.objects.create(
            rack=self.rack,
            tecnico=self.tecnico,
            tipo_actividad=TipoActividad.PREVENTIVO,
            hora_inicio=ahora - timedelta(days=dias_atras),
            hora_fin=(ahora - timedelta(days=dias_atras)) if cerrado else None,
            cerrado=cerrado,
        )

    def _registro_planta(self, cerrado=True, dias_atras=2):
        from django.utils import timezone
        from datetime import timedelta
        ahora = timezone.now()
        registro = RegistroPlanta.objects.create(
            planta=self.planta,
            tecnico=self.tecnico,
            fecha=(ahora - timedelta(days=dias_atras)).date(),
            cerrado=cerrado,
        )
        if cerrado:
            registro.hora_fin = ahora - timedelta(days=dias_atras)
            registro.save(update_fields=['hora_fin'])
        return registro

    def test_requiere_login(self):
        resp = self.client.get(reverse('operations:mis_intervenciones'))
        self.assertEqual(resp.status_code, 302)

    def test_supervisor_redirigido_al_dashboard(self):
        supervisor = get_user_model().objects.create_user(
            username='super1', password='testpass123', rol=Rol.SUPERVISOR
        )
        self.client.login(username='super1', password='testpass123')
        resp = self.client.get(reverse('operations:mis_intervenciones'))
        self.assertRedirects(resp, reverse('analytics:dashboard'))

    def test_lista_cerradas_del_mes_ambos_tipos(self):
        self._registro_rack(cerrado=True, dias_atras=1)
        self._registro_planta(cerrado=True, dias_atras=2)
        self.client.login(username='tecnico1', password='testpass123')
        resp = self.client.get(reverse('operations:mis_intervenciones'))
        self.assertEqual(resp.status_code, 200)
        items = resp.context['intervenciones']
        self.assertEqual(len(items), 2)
        tipos = {item['tipo'] for item in items}
        self.assertEqual(tipos, {'Rack', 'Planta'})

    def test_excluye_abiertas(self):
        self._registro_rack(cerrado=False, dias_atras=1)
        self.client.login(username='tecnico1', password='testpass123')
        resp = self.client.get(reverse('operations:mis_intervenciones'))
        self.assertEqual(resp.context['intervenciones'], [])

    def test_orden_fecha_descendente(self):
        self._registro_rack(cerrado=True, dias_atras=1)
        self._registro_planta(cerrado=True, dias_atras=2)
        self.client.login(username='tecnico1', password='testpass123')
        resp = self.client.get(reverse('operations:mis_intervenciones'))
        fechas = [item['fecha'] for item in resp.context['intervenciones']]
        self.assertEqual(fechas, sorted(fechas, reverse=True))
```

Nota: agregar los imports `from operations.models import RegistroActividad, TipoActividad` junto a los imports existentes.

- [ ] **Step 2: Run test to verify it fails**

Run: `& C:\Users\Usuario\first\venv\Scripts\python.exe manage.py test operations --settings=config.test_settings`
Expected: `NoReverseMatch` / 404 — la URL `operations:mis_intervenciones` no existe.

- [ ] **Step 3: Add the view**

Append after `ScannerView` (line ~40) in `operations/views.py`:

```python
class MisIntervencionesView(TecnicoRequiredMixin, View):
    """Listado de tiendas intervenidas por el técnico en el mes actual."""
    def get(self, request):
        ahora = timezone.now()
        inicio_mes = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        from datetime import timedelta
        mes_siguiente = (inicio_mes + timedelta(days=32)).replace(day=1)

        racks = RegistroActividad.objects.filter(
            tecnico=request.user,
            cerrado=True,
            hora_fin__range=(inicio_mes, mes_siguiente),
        ).select_related('rack__tienda')

        plantas = RegistroPlanta.objects.filter(
            tecnico=request.user,
            cerrado=True,
            hora_fin__range=(inicio_mes, mes_siguiente),
        ).select_related('planta__tienda')

        intervenciones = []
        for r in racks:
            intervenciones.append({
                'tienda': r.rack.tienda.nombre,
                'tipo': 'Rack',
                'fecha': r.hora_fin,
            })
        for p in plantas:
            intervenciones.append({
                'tienda': p.planta.tienda.nombre,
                'tipo': 'Planta',
                'fecha': p.hora_fin,
            })
        intervenciones.sort(key=lambda x: x['fecha'], reverse=True)

        return render(request, 'operations/mis_intervenciones.html', {
            'intervenciones': intervenciones,
        })
```

- [ ] **Step 4: Add the URL**

In `operations/urls.py`, after the scanner path (line 8):

```python
    path('mis-intervenciones/', views.MisIntervencionesView.as_view(), name='mis_intervenciones'),
```

- [ ] **Step 5: Run test to verify it passes**

Run: `& C:\Users\Usuario\first\venv\Scripts\python.exe manage.py test operations --settings=config.test_settings`
Expected: los tests de `MisIntervencionesViewTest` pasan. (El render del template fallará solo si `mis_intervenciones.html` no existe — se crea en Task 2; por eso esta tarea se commitea junto con la Task 2 si fuera necesario, o se crea un stub en el Step 5. Si el test de `test_lista_cerradas_del_mes_ambos_tipos` falla por TemplateDoesNotExist, crear el stub del template en Step 5 antes de correr.)

- [ ] **Step 6: Commit**

```bash
git add operations/views.py operations/urls.py operations/tests.py
git commit -m "feat: vista y URL de tiendas intervenidas del mes"
```

---

### Task 2: Plantilla `mis_intervenciones.html` + botón en el menú

**Files:**
- Create: `templates/operations/mis_intervenciones.html`
- Modify: `templates/base.html:48-53`

**Interfaces:**
- Consumes: URL `operations:mis_intervenciones` y contexto `intervenciones` (Task 1).

- [ ] **Step 1: Create the template**

Create `templates/operations/mis_intervenciones.html`:

```html
{% extends 'base.html' %}
{% block title %}Tiendas intervenidas del mes — SGMR{% endblock %}

{% block content %}
<div class="row justify-content-center">
  <div class="col-12 col-md-9 col-lg-7">
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h1 class="h5 mb-0 fw-bold text-secondary">Tiendas intervenidas este mes</h1>
      <a href="{% url 'operations:scanner' %}" class="btn btn-primary btn-sm">
        <i class="bi bi-upc-scan me-1"></i> Ir al escáner
      </a>
    </div>

    {% if intervenciones %}
    <div class="card shadow-sm border-0 rounded-3">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="table-light">
            <tr>
              <th class="small fw-bold text-muted px-3 py-3">Tienda</th>
              <th class="small fw-bold text-muted px-3 py-3">Tipo</th>
              <th class="small fw-bold text-muted px-3 py-3">Fecha</th>
            </tr>
          </thead>
          <tbody>
            {% for item in intervenciones %}
            <tr>
              <td class="px-3 py-3 fw-semibold">{{ item.tienda }}</td>
              <td class="px-3 py-3">
                {% if item.tipo == 'Rack' %}
                <span class="badge text-bg-primary"><i class="bi bi-cpu me-1"></i>Rack</span>
                {% else %}
                <span class="badge text-bg-warning"><i class="bi bi-lightning-charge me-1"></i>Planta</span>
                {% endif %}
              </td>
              <td class="px-3 py-3 text-muted">{{ item.fecha|date:"d/m/Y" }}</td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </div>
    {% else %}
    <div class="card shadow-sm border-0 rounded-3 p-5 text-center">
      <i class="bi bi-calendar-x fs-1 text-muted d-block mb-3"></i>
      <p class="text-muted mb-0">No has intervenido tiendas este mes.</p>
    </div>
    {% endif %}
  </div>
</div>
{% endblock %}
```

- [ ] **Step 2: Add the menu button**

In `templates/base.html`, replace lines 51-53:

```html
        {% else %}
        <a class="btn btn-outline-light btn-sm me-2" href="{% url 'operations:scanner' %}">Inicio</a>
        <a class="btn btn-outline-light btn-sm me-2" href="{% url 'operations:mis_intervenciones' %}">Tiendas del mes</a>
        {% endif %}
```

- [ ] **Step 3: Run the full test suite**

Run: `& C:\Users\Usuario\first\venv\Scripts\python.exe manage.py test operations --settings=config.test_settings`
Expected: todos los tests pasan (incluye el render del template).

- [ ] **Step 4: Verify no DB drift**

Run: `& C:\Users\Usuario\first\venv\Scripts\python.exe manage.py makemigrations --check --settings=config.test_settings`
Expected: `No changes detected`

- [ ] **Step 5: Manual smoke check**

Con un técnico logueado: verificar el botón "Tiendas del mes" en el menú, entrar, ver el listado (o el mensaje vacío), y que "Ir al escáner" vuelva al scanner.

- [ ] **Step 6: Commit**

```bash
git add templates/operations/mis_intervenciones.html templates/base.html
git commit -m "feat: plantilla y botón de menú para tiendas intervenidas del mes"
```

---

## Self-Review

- **Spec coverage:** botón en el menú (Task 2), una fila por intervención cerrada con tienda/tipo/fecha (Task 1 + plantilla), solo mes actual (filtro `hora_fin__range`), sin PDF ni detalles (plantilla solo muestra 3 columnas), `LOGIN_REDIRECT_URL` sin cambios (no se toca settings.py). ✓
- **Placeholder scan:** sin TBD; todos los códigos concretos. ✓
- **Type consistency:** contexto `intervenciones` (lista de dicts con claves `tienda`, `tipo`, `fecha`) — la plantilla usa `item.tienda`, `item.tipo`, `item.fecha`; la vista produce exactamente esas claves. La URL se nombra `operations:mis_intervenciones` en vista, urls, plantilla y botón. ✓
