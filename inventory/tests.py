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
