from django.db import models


class Tienda(models.Model):
    """Sucursal donde está instalado el rack."""
    nombre = models.CharField(max_length=200)
    codigo = models.CharField(max_length=50, unique=True, blank=True)
    direccion = models.CharField(max_length=300, blank=True)

    class Meta:
        verbose_name = 'Tienda'
        verbose_name_plural = 'Tiendas'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Rack(models.Model):
    """
    Activo (rack de refrigeración). El QR contiene id_qr que identifica este registro.
    """
    id_qr = models.CharField(max_length=100, unique=True, db_index=True,
                             help_text='ID único en el código QR del rack')
    tienda = models.ForeignKey(Tienda, on_delete=models.PROTECT, related_name='racks')
    marca = models.CharField(max_length=100, blank=True)
    modelo = models.CharField(max_length=100, blank=True)
    refigerante= models.CharField(max_length=100, blank=True)
    ubicacion = models.CharField(max_length=200, blank=True,
                                help_text='Ej: Bodega norte, Pasillo 3')
    compresores_media = models.PositiveSmallIntegerField(default=0,
                                                        verbose_name='Cantidad compresores media')
    compresores_baja = models.PositiveSmallIntegerField(default=0,
                                                       verbose_name='Cantidad compresores baja')
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Rack'
        verbose_name_plural = 'Racks'
        ordering = ['tienda', 'id_qr']

    def __str__(self):
        return f'{self.id_qr} — {self.tienda.nombre}'

    @property
    def total_compresores(self):
        return (self.compresores_media or 0) + (self.compresores_baja or 0)
