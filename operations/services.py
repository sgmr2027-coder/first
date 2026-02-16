"""
Lógica del cronómetro y validaciones de negocio.
"""
from django.utils import timezone
from django.db.models import Q

from .models import RegistroActividad, TipoActividad


def tecnico_tiene_tarea_abierta(tecnico):
    """True si el técnico tiene un registro sin cerrar (sin hora_fin)."""
    return RegistroActividad.objects.filter(
        tecnico=tecnico,
        hora_fin__isnull=True,
        cerrado=False
    ).exists()


def obtener_tarea_abierta(tecnico):
    """Devuelve el RegistroActividad abierto del técnico o None."""
    return RegistroActividad.objects.filter(
        tecnico=tecnico,
        hora_fin__isnull=True,
        cerrado=False
    ).first()


def iniciar_actividad(tecnico, rack, tipo_actividad):
    """
    Crea el registro y arranca el cronómetro en el servidor.
    Lanza ValueError si el técnico ya tiene una tarea abierta.
    """
    if tecnico_tiene_tarea_abierta(tecnico):
        raise ValueError('Ya tienes una tarea abierta en otro rack. Ciérrala antes de iniciar una nueva.')
    if tipo_actividad not in [c[0] for c in TipoActividad.choices]:
        raise ValueError('Tipo de actividad no válido.')
    return RegistroActividad.objects.create(
        rack=rack,
        tecnico=tecnico,
        tipo_actividad=tipo_actividad,
        hora_inicio=timezone.now(),
    )


def duracion_minutos(hora_inicio, hora_fin):
    """Calcula duración en minutos. None si falta hora_fin."""
    if not hora_fin:
        return None
    delta = hora_fin - hora_inicio
    return round(delta.total_seconds() / 60, 1)


def es_duracion_sospechosa(minutos, umbral_minutos=5):
    """Alertar si el tiempo es sospechosamente corto (ej. &lt; 5 min)."""
    if minutos is None:
        return False
    return minutos < umbral_minutos
