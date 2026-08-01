# 3 Corrientes por Compresor (Amp 1/2/3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que cada compresor de un rack registre 3 corrientes (Amp 1/2/3, una por fase, sistema trifásico) en check-in, check-out y el PDF de la intervención.

**Architecture:** Los formularios dinámicos (`ParametrosEntradaForm`/`ParametrosSalidaForm`) generan 3 campos numéricos por compresor (`corriente1/2/3_compresor_{i}`) en lugar de 1. `get_compresores()` expone `corriente_1/2/3` por compresor para las plantillas. El PDF ya lee esas 3 claves; se añade un helper puro `_corriente_por_fase()` con fallback histórico (registros viejos con una sola `corriente_compresor_{i}`) y se corrigen las columnas de `reporte_pdf.html`. Datos en JSON existente — sin cambios de modelos ni migraciones.

**Tech Stack:** Django 5.2, forms dinámicos, JSON (`datos_entrada`/`datos_salida`), xhtml2pdf, test runner con `config/test_settings.py`.

## Global Constraints

- No cambiar modelos, BD, migraciones, URLs ni scanner.
- BD de producción es Supabase PostgreSQL: **jamás** correr `manage.py test` sin `--settings=config.test_settings`.
- Claves por compresor: `corriente1_compresor_{i}`, `corriente2_compresor_{i}`, `corriente3_compresor_{i}` — coinciden con lo que `IntervencionPDFView` ya lee.
- Etiquetas UI/PDF: "Amp 1", "Amp 2", "Amp 3" (sufijo "(media)"/"(baja)" según grupo del compresor).
- Los registros antiguos (clave `corriente_compresor_{i}`) deben seguir legibles en el PDF (fallback → Amp 1).
- Sin comentarios nuevos salvo los del patrón existente.

---

### Task 1: Formularios — 3 campos de corriente por compresor

**Files:**
- Modify: `operations/forms.py:27-42` (`_corriente_field` → generar 3 campos)
- Modify: `operations/forms.py:61-73` (`ParametrosEntradaForm.__init__`)
- Modify: `operations/forms.py:129-143` (`ParametrosSalidaForm.__init__`)
- Modify: `operations/forms.py:90-103` (`ParametrosEntradaForm.get_compresores`)
- Modify: `operations/forms.py:155-172` (`ParametrosSalidaForm.get_compresores`)
- Test: `operations/tests.py` (añadir `CorrienteCompresorFormsTest`)

**Interfaces:**
- Produces: claves de formulario `corriente1_compresor_{i}`, `corriente2_compresor_{i}`, `corriente3_compresor_{i}` y claves de `get_compresores()` → `corriente_1/2/3` que consumen las plantillas (Task 2).

- [ ] **Step 1: Write the failing tests**

Append to `operations/tests.py`:

```python
from operations.forms import ParametrosEntradaForm, ParametrosSalidaForm
from operations.views import _corriente_por_fase


class CorrienteCompresorFormsTest(TestCase):
    def setUp(self):
        tienda = Tienda.objects.create(nombre='Tienda A', codigo='A')
        self.rack = Rack.objects.create(
            id_qr='RACK-001', tienda=tienda,
            compresores_media=1, compresores_baja=1, activo=True,
        )

    def test_entrada_genera_3_campos_por_compresor(self):
        form = ParametrosEntradaForm(rack=self.rack)
        self.assertIn('corriente1_compresor_1', form.fields)
        self.assertIn('corriente2_compresor_1', form.fields)
        self.assertIn('corriente3_compresor_1', form.fields)
        self.assertIn('corriente1_compresor_2', form.fields)
        self.assertIn('corriente2_compresor_2', form.fields)
        self.assertIn('corriente3_compresor_2', form.fields)

    def test_salida_genera_3_campos_por_compresor(self):
        form = ParametrosSalidaForm(rack=self.rack)
        self.assertIn('corriente1_compresor_1', form.fields)
        self.assertIn('corriente2_compresor_1', form.fields)
        self.assertIn('corriente3_compresor_1', form.fields)

    def test_entrada_get_compresores_expone_3_corrientes(self):
        form = ParametrosEntradaForm(rack=self.rack)
        grupos = form.get_compresores()
        c1 = grupos['media'][0]
        self.assertIn('corriente_1', c1)
        self.assertIn('corriente_2', c1)
        self.assertIn('corriente_3', c1)

    def test_salida_get_compresores_expone_3_corrientes(self):
        form = ParametrosSalidaForm(rack=self.rack)
        grupos = form.get_compresores()
        c2 = grupos['baja'][0]
        self.assertIn('corriente_1', c2)
        self.assertIn('corriente_2', c2)
        self.assertIn('corriente_3', c2)

    def test_etiquetas_amp_por_fase(self):
        form = ParametrosEntradaForm(rack=self.rack)
        self.assertEqual(form.fields['corriente1_compresor_1'].label, 'Amp 1 (media)')
        self.assertEqual(form.fields['corriente2_compresor_1'].label, 'Amp 2 (media)')
        self.assertEqual(form.fields['corriente3_compresor_1'].label, 'Amp 3 (media)')
        self.assertEqual(form.fields['corriente1_compresor_2'].label, 'Amp 1 (baja)')
```

Nota: `operations/tests.py` ya importa `TestCase`, `Rack`, `Tienda` en el archivo — añadir solo los imports de forms/views arriba.

- [ ] **Step 2: Run tests to verify they fail**

Run: `& <venv>\python.exe manage.py test operations --settings=config.test_settings`
Expected: `AssertionError` en `test_entrada_genera_3_campos_por_compresor` (campo `corriente1_compresor_1` no existe) y `ImportError` para `_corriente_por_fase`.

- [ ] **Step 3: Replace `_corriente_field` with a 3-field generator**

In `operations/forms.py`, replace lines 27-42:

```python
def _corriente_fields(numero, etiqueta_extra=''):
    """3 campos de corriente (Amp 1/2/3) para un compresor trifásico."""
    fields = {}
    for fase in (1, 2, 3):
        label = f'Amp {fase} {etiqueta_extra}'.strip()
        fields[f'corriente{fase}_compresor_{numero}'] = forms.DecimalField(
            label=label,
            required=False,
            min_value=0,
            max_digits=6,
            decimal_places=2,
            widget=forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'A',
                'data-label': label,
            })
        )
    return fields
```

- [ ] **Step 4: Update `ParametrosEntradaForm.__init__`**

Replace lines 71-73:

```python
            for i in range(1, n + 1):
                etiqueta = '(media)' if i <= media else '(baja)'
                self.fields.update(_corriente_fields(i, etiqueta))
```

- [ ] **Step 5: Update `ParametrosEntradaForm.get_compresores`**

Replace the `groups[temp_key].append({...})` block (lines 99-102):

```python
            groups[temp_key].append({
                'numero': i,
                'corriente_1': self.get(f'corriente1_compresor_{i}'),
                'corriente_2': self.get(f'corriente2_compresor_{i}'),
                'corriente_3': self.get(f'corriente3_compresor_{i}'),
            })
```

- [ ] **Step 6: Update `ParametrosSalidaForm.__init__`**

Replace lines 135-137:

```python
            for i in range(1, n + 1):
                etiqueta = '(media)' if i <= media else '(baja)'
                self.fields.update(_corriente_fields(i, etiqueta))
```

- [ ] **Step 7: Update `ParametrosSalidaForm.get_compresores`**

Replace the `groups[temp_key].append({...})` block (lines 162-171):

```python
            groups[temp_key].append({
                'numero': i,
                'corriente_1': self[f'corriente1_compresor_{i}'],
                'corriente_2': self[f'corriente2_compresor_{i}'],
                'corriente_3': self[f'corriente3_compresor_{i}'],
                'estado_aceite': self[f'estado_aceite_{i}'],
                'nivel_aceite': self[f'nivel_aceite_{i}'],
                'ruido': self[f'ruido_{i}'],
                'dispara_aceite': self[f'dispara_aceite_{i}'],
                'dispara_presion': self[f'dispara_presion_{i}'],
                'funciona_traxoil': self[f'funciona_traxoil_{i}'],
            })
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `& <venv>\python.exe manage.py test operations --settings=config.test_settings`
Expected: tests de `CorrienteCompresorFormsTest` pasan (excepto los de `_corriente_por_fase`, aún sin definir).

- [ ] **Step 9: Commit**

```bash
git add operations/forms.py operations/tests.py
git commit -m "feat: 3 campos de corriente por compresor en formularios"
```

---

### Task 2: Helper de PDF con fallback histórico

**Files:**
- Modify: `operations/views.py:350-375` (`IntervencionPDFView`) — usar helper
- Test: `operations/tests.py` (añadir tests de `_corriente_por_fase`)

**Interfaces:**
- Consumes: claves `corriente1/2/3_compresor_{i}` (Task 1) y `corriente_compresor_{i}` (históricos).
- Produces: tupla `(corriente_1, corriente_2, corriente_3)` que la plantilla PDF consume (Task 3).

- [ ] **Step 1: Write the failing tests**

Append to `operations/tests.py` (dentro de `CorrienteCompresorFormsTest`):

```python
    def test_corriente_por_fase_con_3_fases(self):
        datos = {
            'corriente1_compresor_1': '5.5',
            'corriente2_compresor_1': '5.6',
            'corriente3_compresor_1': '5.7',
        }
        self.assertEqual(_corriente_por_fase(datos, 1), ('5.5', '5.6', '5.7'))

    def test_corriente_por_fase_fallback_historico(self):
        datos = {'corriente_compresor_1': '5.5'}
        self.assertEqual(_corriente_por_fase(datos, 1), ('5.5', '—', '—'))

    def test_corriente_por_fase_ausente(self):
        self.assertEqual(_corriente_por_fase({}, 3), ('—', '—', '—'))

    def test_corriente_por_fase_no_cae_con_valor_cero(self):
        datos = {'corriente1_compresor_1': 0.0, 'corriente_compresor_1': '5.5'}
        self.assertEqual(_corriente_por_fase(datos, 1), (0.0, '—', '—'))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `& <venv>\python.exe manage.py test operations --settings=config.test_settings`
Expected: `NameError: name '_corriente_por_fase' is not defined`.

- [ ] **Step 3: Add the helper function**

Add before `class IntervencionPDFView` (after the `link_callback` function, ~line 343):

```python
def _corriente_por_fase(datos, i):
    """Devuelve (corriente_1, corriente_2, corriente_3) de un compresor con fallback histórico."""
    c1 = datos.get(f'corriente1_compresor_{i}')
    if c1 is None:
        c1 = datos.get(f'corriente_compresor_{i}')
    return (
        c1 if c1 is not None else '—',
        datos.get(f'corriente2_compresor_{i}', '—'),
        datos.get(f'corriente3_compresor_{i}', '—'),
    )
```

- [ ] **Step 4: Use the helper in `IntervencionPDFView`**

Replace lines 362-375:

```python
            detalle = detalles_map.get(i)
            corriente_1, corriente_2, corriente_3 = _corriente_por_fase(datos, i)
            comp_data = {
                'numero': i,
                'modelo': detalle.modelo if detalle else '—',
                'serie': detalle.serie if detalle else '—',
                'corriente_1': corriente_1,
                'corriente_2': corriente_2,
                'corriente_3': corriente_3,
                'estado_aceite': datos.get(f'estado_aceite_{i}', '—'),
                'nivel_aceite': datos.get(f'nivel_aceite_{i}', '—'),
                'ruido': datos.get(f'ruido_{i}', '—'),
                'dispara_aceite': datos.get(f'dispara_aceite_{i}', '—'),
                'dispara_presion': datos.get(f'dispara_presion_{i}', '—'),
                'funciona_traxoil': datos.get(f'funciona_traxoil_{i}', '—'),
            }
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `& <venv>\python.exe manage.py test operations --settings=config.test_settings`
Expected: todos los tests de `_corriente_por_fase` pasan.

- [ ] **Step 6: Commit**

```bash
git add operations/views.py operations/tests.py
git commit -m "feat: helper de corrientes por fase con fallback histórico en PDF"
```

---

### Task 3: Plantillas check-in, check-out y PDF

**Files:**
- Modify: `templates/operations/checkin.html:443-456` (tabla media) y `:469-483` (tabla baja)
- Modify: `templates/operations/checkout.html:533-557` (tabla media) y `:571-595` (tabla baja)
- Modify: `templates/operations/reporte_pdf.html:312-338` (media) y `:352-378` (baja) + colspans `:341` y `:380`

**Interfaces:**
- Consumes: `corriente_1/2/3` por compresor de `get_compresores()` (Task 1) y del contexto del PDF (Task 2).

- [ ] **Step 1: Update `checkin.html` — tabla media**

Replace the header row (lines 443-446) and the row body (lines 449-456):

```html
              <tr>
                <th style="width:42px; text-align:center;">C#</th>
                <th>Amp 1</th>
                <th>Amp 2</th>
                <th>Amp 3</th>
              </tr>
            </thead>
            <tbody>
              {% for c in comps.media %}
              <tr>
                <td>
                  <div class="c-num media">{{ c.numero }}</div>
                </td>
                <td style="min-width:90px;">{{ c.corriente_1 }}</td>
                <td style="min-width:90px;">{{ c.corriente_2 }}</td>
                <td style="min-width:90px;">{{ c.corriente_3 }}</td>
              </tr>
              {% endfor %}
```

- [ ] **Step 2: Update `checkin.html` — tabla baja**

Same replacement using `comps.baja` / `c-num baja` (lines 469-483).

- [ ] **Step 3: Update `checkout.html` — tabla media**

Replace the header (lines 533-542) adding 2 columnas "Amp 2"/"Amp 3" tras "Amp 1", y en la fila (lines 545-558) reemplazar `{{ c.corriente }}` por 3 `<td>` con `{{ c.corriente_1 }}`, `{{ c.corriente_2 }}`, `{{ c.corriente_3 }}`:

```html
              <tr>
                <th style="width:42px; text-align:center;">C#</th>
                <th>Amp 1</th>
                <th>Amp 2</th>
                <th>Amp 3</th>
                <th>Aceite</th>
                <th>Nivel</th>
                <th>Ruido</th>
                <th class="text-center">Dispara por Aceite</th>
                <th class="text-center">Dispara por Presión</th>
                <th class="text-center">Traxoil Funcional</th>
              </tr>
            </thead>
            <tbody>
              {% for c in comps.media %}
              <tr>
                <td>
                  <div class="c-num media">{{ c.numero }}</div>
                </td>
                <td style="min-width:80px;">{{ c.corriente_1 }}</td>
                <td style="min-width:80px;">{{ c.corriente_2 }}</td>
                <td style="min-width:80px;">{{ c.corriente_3 }}</td>
                <td style="min-width:110px;">{{ c.estado_aceite }}</td>
                <td style="min-width:110px;">{{ c.nivel_aceite }}</td>
                <td style="min-width:110px;">{{ c.ruido }}</td>
                <td class="text-center">{{ c.dispara_aceite }}</td>
                <td class="text-center">{{ c.dispara_presion }}</td>
                <td class="text-center">{{ c.funciona_traxoil }}</td>
              </tr>
              {% endfor %}
```

- [ ] **Step 4: Update `checkout.html` — tabla baja**

Same replacement usando `comps.baja` / `c-num baja` (lines 571-595).

- [ ] **Step 5: Update `reporte_pdf.html` — tabla media**

Header (lines 312-323): sustituir la columna `<th style="width: 8%;">Corriente</th>` por 3 columnas:

```html
                <th style="width: 6%;">Amp 1</th>
                <th style="width: 6%;">Amp 2</th>
                <th style="width: 6%;">Amp 3</th>
```

Fila (line 331): reemplazar `<td class="td-bold">{{ c.corriente }}</td>` por:

```html
                <td class="td-bold">{{ c.corriente_1 }}</td>
                <td class="td-bold">{{ c.corriente_2 }}</td>
                <td class="td-bold">{{ c.corriente_3 }}</td>
```

Colspan vacío (line 341): `colspan="10"` → `colspan="12"`.

- [ ] **Step 6: Update `reporte_pdf.html` — tabla baja**

Mismo cambio (header líneas 352-363, fila línea 371, colspan línea 380 `colspan="10"` → `colspan="12"`).

- [ ] **Step 7: Run the full test suite**

Run: `& <venv>\python.exe manage.py test operations --settings=config.test_settings`
Expected: todos los tests pasan.

- [ ] **Step 8: Verify no DB drift**

Run: `& <venv>\python.exe manage.py makemigrations --check --settings=config.test_settings`
Expected: `No changes detected`

- [ ] **Step 9: Manual smoke check**

Con un técnico logueado: crear actividad en un rack con compresores, verificar en check-in y check-out que cada compresor muestra 3 inputs (Amp 1/2/3), guardar, abrir el PDF y confirmar 3 columnas por compresor.

- [ ] **Step 10: Commit**

```bash
git add templates/operations/checkin.html templates/operations/checkout.html templates/operations/reporte_pdf.html
git commit -m "feat: 3 columnas de corriente (Amp 1/2/3) en check-in, check-out y PDF"
```

---

## Self-Review

- **Spec coverage:** 3 campos por compresor en ambos formularios (Task 1), fallback histórico (Task 2), 3 columnas en check-in/checkout/PDF + corrección de columna vacía del PDF (Task 3). Sin modelos/BD/migraciones. ✓
- **Placeholder scan:** sin TBD; todos los códigos concretos. Los `colspan` se actualizan a 12 en ambos lugares (media y baja). ✓
- **Type consistency:** claves de formulario `corriente1/2/3_compresor_{i}`; claves de `get_compresores` y contexto PDF `corriente_1/2/3`; el helper `_corriente_por_fase(datos, i)` devuelve tupla `(corriente_1, corriente_2, corriente_3)`. Todas coinciden entre Task 1, 2 y 3. ✓
