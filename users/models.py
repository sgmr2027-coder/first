from django.contrib.auth.models import AbstractUser
from django.db import models


class Rol(models.TextChoices):
    TECNICO = 'tecnico', 'Técnico'
    SUPERVISOR = 'supervisor', 'Supervisor'


class Tecnico(AbstractUser):
    """Perfil de técnico o supervisor. Solo técnicos activos pueden hacer login."""
    rol = models.CharField(max_length=20, choices=Rol.choices, default=Rol.TECNICO)
    activo = models.BooleanField(default=True)
    nombre_completo = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = 'Técnico'
        verbose_name_plural = 'Técnicos'

    def __str__(self):
        return self.get_full_name() or self.username

    def save(self, *args, **kwargs):
        if not self.nombre_completo and (self.first_name or self.last_name):
            self.nombre_completo = f'{self.first_name or ""} {self.last_name or ""}'.strip()
        super().save(*args, **kwargs)
