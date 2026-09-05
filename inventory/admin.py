from django.contrib import admin
from .models import (
    Zona, Tienda, Rack, Compresor, PlantaElectrica, RegistroPlanta,
    AsignacionTecnico,
)


@admin.register(Zona)
class ZonaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion', 'total_tiendas', 'activo')
    search_fields = ('nombre',)
    list_editable = ('activo',)

    @admin.display(description='Tiendas')
    def total_tiendas(self, obj):
        return obj.tiendas.count()


@admin.register(Tienda)
class TiendaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo', 'zona', 'direccion')
    list_filter = ('zona',)
    search_fields = ('nombre', 'codigo')
    list_editable = ('zona',)


@admin.register(AsignacionTecnico)
class AsignacionTecnicoAdmin(admin.ModelAdmin):
    list_display = ('tecnico', 'tienda', 'zona_tienda', 'especialidad', 'activo')
    list_filter = ('especialidad', 'activo', 'tienda__zona', 'tecnico')
    search_fields = ('tecnico__username', 'tecnico__first_name', 'tecnico__last_name', 'tienda__nombre')
    list_editable = ('activo',)
    autocomplete_fields = ('tienda',)

    @admin.display(description='Zona')
    def zona_tienda(self, obj):
        return obj.tienda.zona


class CompresorInline(admin.TabularInline):
    model = Compresor
    extra = 0
    fields = ('numero', 'temperatura', 'modelo', 'serie')


@admin.register(Rack)
class RackAdmin(admin.ModelAdmin):
    list_display = ('id_qr', 'tienda', 'marca', 'refigerante', 'ubicacion', 'compresores_media', 'compresores_baja', 'activo')
    list_filter = ('tienda', 'activo')
    search_fields = ('id_qr', 'marca', 'tienda__nombre')
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
