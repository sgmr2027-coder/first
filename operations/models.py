from django.db import models
from django.conf import settings
from inventory.models import Rack


class TipoActividad(models.TextChoices):
    PREVENTIVO = 'preventivo', 'Mantenimiento Preventivo'
    CORRECTIVO = 'correctivo', 'Mantenimiento Correctivo'
    EMERGENCIA = 'emergencia', 'Emergencia'


class RegistroActividad(models.Model):
    """
    Bitácora: una intervención sobre un rack.
    hora_inicio se registra al elegir tipo; hora_fin al finalizar.
    Datos de entrada y salida en JSON para comparar antes/después.
    """
    rack = models.ForeignKey(Rack, on_delete=models.PROTECT, related_name='registros')
    tecnico = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='registros_actividad'
    )
    tipo_actividad = models.CharField(
        max_length=20,
        choices=TipoActividad.choices
    )
    hora_inicio = models.DateTimeField()
    hora_fin = models.DateTimeField(null=True, blank=True)
    datos_entrada = models.JSONField(
        default=dict,
        blank=True,
        help_text='Presiones, temperaturas, setpoints, amperajes al inicio'
    )
    datos_salida = models.JSONField(
        default=dict,
        blank=True,
        help_text='Parámetros finales para comparar'
    )
    observaciones = models.TextField(blank=True)
    cerrado = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Registro de actividad'
        verbose_name_plural = 'Registros de actividad'
        ordering = ['-hora_inicio']

    def __str__(self):
        return f'{self.get_tipo_actividad_display()} — {self.rack} — {self.tecnico}'

    def duracion_minutos(self):
        if not self.hora_fin:
            return None
        delta = self.hora_fin - self.hora_inicio
        return round(delta.total_seconds() / 60, 1)

    def marcar_cerrado(self):
        self.cerrado = True
        self.save(update_fields=['cerrado', 'hora_fin'])
