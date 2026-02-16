from django.contrib import admin
from .models import RegistroActividad


@admin.register(RegistroActividad)
class RegistroActividadAdmin(admin.ModelAdmin):
    list_display = ('id', 'rack', 'tecnico', 'tipo_actividad', 'hora_inicio', 'hora_fin', 'cerrado')
    list_filter = ('tipo_actividad', 'cerrado')
    search_fields = ('rack__id_qr', 'tecnico__username')
    readonly_fields = ('hora_inicio', 'hora_fin')
