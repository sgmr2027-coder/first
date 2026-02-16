from django.contrib import admin
from .models import Tienda, Rack


@admin.register(Tienda)
class TiendaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo', 'direccion')
    search_fields = ('nombre', 'codigo')


@admin.register(Rack)
class RackAdmin(admin.ModelAdmin):
    list_display = ('id_qr', 'tienda', 'marca', 'refigerante', 'ubicacion', 'compresores_media', 'compresores_baja', 'activo')
    list_filter = ('tienda', 'activo')
    search_fields = ('id_qr', 'marca', 'tienda__nombre')
