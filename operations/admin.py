from django.contrib import admin
from inventory.models import Tienda, Rack, Compresor, PlantaElectrica, RegistroPlanta
from .models import RegistroActividad
 
 
# ─────────────────────────────────────────────────────────────────────────────
# INVENTORY
# ─────────────────────────────────────────────────────────────────────────────
 
@admin.register(Tienda)
class TiendaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo', 'direccion')
    search_fields = ('nombre', 'codigo')
 
 
class CompresorInline(admin.TabularInline):
    model = Compresor
    extra = 0
    fields = ('numero', 'temperatura', 'modelo', 'serie')
 
 
@admin.register(Rack)
class RackAdmin(admin.ModelAdmin):
    list_display = ('id_qr', 'tienda', 'marca', 'modelo', 'ubicacion',
                    'compresores_media', 'compresores_baja', 'activo')
    list_filter = ('activo', 'tienda')
    search_fields = ('id_qr', 'marca', 'modelo')
    list_editable = ('activo',)
    inlines = [CompresorInline]
 
 
@admin.register(PlantaElectrica)
class PlantaElectricaAdmin(admin.ModelAdmin):
    list_display = ('id_qr', 'tienda', 'marca', 'modelo', 'capacidad_kva', 'ubicacion', 'activo')
    list_filter = ('activo', 'tienda')
    search_fields = ('id_qr', 'marca', 'modelo', 'serie')
    list_editable = ('activo',)
 
 
@admin.register(RegistroPlanta)
class RegistroPlantaAdmin(admin.ModelAdmin):
    list_display = ('planta', 'tecnico', 'fecha', 'hora_inicio', 'hora_fin', 'cerrado')
    list_filter = ('cerrado', 'fecha', 'planta__tienda')
    search_fields = ('planta__id_qr', 'planta__tienda__nombre', 'tecnico__username')
    readonly_fields = ('hora_inicio',)
 
    fieldsets = (
        ('Identificación', {
            'fields': ('planta', 'tecnico', 'fecha', 'hora_inicio', 'hora_fin', 'cerrado')
        }),
        ('Batería', {
            'fields': ('bateria_cantidad', 'bateria_modelo',
                       'bateria_fecha_instalacion', 'bateria_estado_cargador', 'bateria_nivel_carga')
        }),
        ('Fluidos y componentes', {
            'fields': ('fugas_aceite_combustible', 'nivel_combustible', 'tipo_radiador',
                       'nivel_agua_radiador', 'nivel_aceite', 'horas_funcionamiento', 'obstruccion')
        }),
        ('Voltajes L-L', {
            'fields': ('voltaje_l1l2', 'voltaje_l2l3', 'voltaje_l1l3')
        }),
        ('Voltajes L-N', {
            'fields': ('voltaje_l1n', 'voltaje_l2n', 'voltaje_l3n')
        }),
        ('Amperajes', {
            'fields': ('amperaje_a1', 'amperaje_a2', 'amperaje_a3')
        }),
        ('Lectura de datos', {
            'fields': ('voltaje_generador', 'frecuencia_hz', 'rpm', 'voltaje_dc_cargador')
        }),
        ('Arranque / Transferencia', {
            'fields': ('arranque_vacio', 'prueba_transferencia_carga')
        }),
        ('Observaciones', {
            'fields': ('observaciones',)
        }),
    )
 
 
# ─────────────────────────────────────────────────────────────────────────────
# OPERATIONS
# ─────────────────────────────────────────────────────────────────────────────
 
@admin.register(RegistroActividad)
class RegistroActividadAdmin(admin.ModelAdmin):
    list_display = ('id', 'rack', 'tecnico', 'tipo_actividad', 'hora_inicio', 'hora_fin', 'cerrado')
    list_filter = ('tipo_actividad', 'cerrado')
    search_fields = ('rack__id_qr', 'tecnico__username')
    readonly_fields = ('hora_inicio', 'hora_fin')