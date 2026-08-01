from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from inventory.models import PlantaElectrica, Rack, RegistroPlanta, Tienda
from users.models import Rol
from operations.forms import ParametrosEntradaForm, ParametrosSalidaForm
from operations.models import RegistroActividad, TipoActividad
from operations.views import _corriente_por_fase


class ScannerViewTest(TestCase):
    def setUp(self):
        tienda_a = Tienda.objects.create(nombre='Tienda A', codigo='A')
        Tienda.objects.create(nombre='Tienda B', codigo='B')
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

    def test_scanner_html_incluye_dropdowns_y_datos_json(self):
        self.client.login(username='tecnico1', password='testpass123')
        resp = self.client.get(reverse('operations:scanner'))
        html = resp.content.decode()
        self.assertIn('id="select_tienda"', html)
        self.assertIn('id="select_equipo"', html)
        self.assertIn('id="sin_equipos"', html)
        self.assertIn('id="racks-data"', html)
        self.assertIn('id="plantas-data"', html)
        self.assertIn('"RACK-001"', html)
        self.assertIn('Tienda B', html)


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


class MisIntervencionesViewTest(TestCase):
    def setUp(self):
        self.tienda = Tienda.objects.create(nombre='Tienda A', codigo='A')
        self.rack = Rack.objects.create(id_qr='RACK-001', tienda=self.tienda, activo=True)
        self.planta = PlantaElectrica.objects.create(id_qr='PLANTA-001', tienda=self.tienda, activo=True)
        self.tecnico = get_user_model().objects.create_user(
            username='tecnico1', password='testpass123', rol=Rol.TECNICO
        )

    def _fin_dentro_del_mes(self, dia):
        ahora = timezone.now()
        inicio_mes = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return inicio_mes + timedelta(days=dia - 1, hours=12)

    def _registro_rack(self, cerrado=True, dia_mes=5):
        fin = self._fin_dentro_del_mes(dia_mes)
        return RegistroActividad.objects.create(
            rack=self.rack,
            tecnico=self.tecnico,
            tipo_actividad=TipoActividad.PREVENTIVO,
            hora_inicio=fin,
            hora_fin=fin if cerrado else None,
            cerrado=cerrado,
        )

    def _registro_planta(self, cerrado=True, dia_mes=3):
        fin = self._fin_dentro_del_mes(dia_mes)
        registro = RegistroPlanta.objects.create(
            planta=self.planta,
            tecnico=self.tecnico,
            fecha=fin.date(),
            cerrado=cerrado,
        )
        if cerrado:
            registro.hora_fin = fin
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
        self._registro_rack(cerrado=True, dia_mes=5)
        self._registro_planta(cerrado=True, dia_mes=3)
        self.client.login(username='tecnico1', password='testpass123')
        resp = self.client.get(reverse('operations:mis_intervenciones'))
        self.assertEqual(resp.status_code, 200)
        items = resp.context['intervenciones']
        self.assertEqual(len(items), 2)
        self.assertEqual({item['tipo'] for item in items}, {'Rack', 'Planta'})

    def test_excluye_abiertas(self):
        self._registro_rack(cerrado=False, dia_mes=5)
        self.client.login(username='tecnico1', password='testpass123')
        resp = self.client.get(reverse('operations:mis_intervenciones'))
        self.assertEqual(resp.context['intervenciones'], [])

    def test_orden_fecha_descendente(self):
        self._registro_rack(cerrado=True, dia_mes=5)
        self._registro_planta(cerrado=True, dia_mes=3)
        self.client.login(username='tecnico1', password='testpass123')
        resp = self.client.get(reverse('operations:mis_intervenciones'))
        fechas = [item['fecha'] for item in resp.context['intervenciones']]
        self.assertEqual(fechas, sorted(fechas, reverse=True))
