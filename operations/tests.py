from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from inventory.models import PlantaElectrica, Rack, Tienda
from users.models import Rol


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
