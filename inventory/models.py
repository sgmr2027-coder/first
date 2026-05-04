from django.db import models
from django.conf import settings


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
    refigerante = models.CharField(max_length=100, blank=True)
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


class Compresor(models.Model):
    """
    Detalle técnico de cada compresor individual en un rack.
    """
    class Temperatura(models.TextChoices):
        MEDIA = 'media', 'Media Temperatura'
        BAJA = 'baja', 'Baja Temperatura'

    rack = models.ForeignKey(Rack, on_delete=models.CASCADE, related_name='detalles_compresores')
    numero = models.PositiveSmallIntegerField(help_text='Ej: 1, 2, 3...')
    temperatura = models.CharField(max_length=10, choices=Temperatura.choices)
    modelo = models.CharField(max_length=100, blank=True)
    serie = models.CharField(max_length=100, blank=True, verbose_name='Número de serie')

    class Meta:
        verbose_name = 'Detalle de compresor'
        verbose_name_plural = 'Detalles de compresores'
        ordering = ['rack', 'temperatura', 'numero']
        unique_together = ['rack', 'numero']

    def __str__(self):
        return f'C{self.numero} ({self.get_temperatura_display()}) — {self.rack.id_qr}'

# ─────────────────────────────────────────────────────────────────────────────
# PLANTA ELÉCTRICA
# ─────────────────────────────────────────────────────────────────────────────

class PlantaElectrica(models.Model):
    """
    Activo (planta eléctrica / generador). El QR contiene id_qr que identifica este registro.
    Sigue la misma lógica que Rack.
    """
    id_qr = models.CharField(
        max_length=100, unique=True, db_index=True,
        help_text='ID único en el código QR de la planta'
    )
    tienda = models.ForeignKey(Tienda, on_delete=models.PROTECT, related_name='plantas_electricas')
    marca = models.CharField(max_length=100, blank=True)
    modelo = models.CharField(max_length=100, blank=True)
    serie = models.CharField(max_length=100, blank=True, verbose_name='Número de serie')
    capacidad_kva = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        verbose_name='Capacidad (KVA)'
    )
    ubicacion = models.CharField(max_length=200, blank=True,
                                 help_text='Ej: Patio trasero, Cuarto de máquinas')
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Planta Eléctrica'
        verbose_name_plural = 'Plantas Eléctricas'
        ordering = ['tienda', 'id_qr']

    def __str__(self):
        return f'{self.id_qr} — {self.tienda.nombre}'


class RegistroPlanta(models.Model):
    """
    Checklist de revisión mensual de una PlantaElectrica.
    Mapea campo a campo el 'Formato de Revisión Mensual de Plantas Eléctricas' de Olímpica.
    """

    class EstadoGeneral(models.TextChoices):
        BUENO   = 'bueno',   'Bueno'
        REGULAR = 'regular', 'Regular'
        MALO    = 'malo',    'Malo'
        NA      = 'na',      'N/A'

    # ── Identificación ───────────────────────────────────────────────────────
    planta      = models.ForeignKey(PlantaElectrica, on_delete=models.PROTECT, related_name='registros')
    tecnico     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='registros_planta')
    fecha       = models.DateField()
    hora_inicio = models.DateTimeField(auto_now_add=True)
    hora_fin    = models.DateTimeField(null=True, blank=True)
    cerrado     = models.BooleanField(default=False)

    # ── Batería ──────────────────────────────────────────────────────────────
    bateria_cantidad          = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name='Cantidad de baterías')
    bateria_modelo            = models.CharField(max_length=100, blank=True, verbose_name='Modelo de batería')
    bateria_fecha_instalacion = models.DateField(null=True, blank=True, verbose_name='Fecha instalación batería')
    bateria_estado_cargador   = models.CharField(max_length=20, choices=EstadoGeneral.choices, blank=True, verbose_name='Estado cargador')
    bateria_nivel_carga       = models.CharField(max_length=20, choices=EstadoGeneral.choices, blank=True, verbose_name='Nivel de carga')

    # ── Fluidos y componentes ────────────────────────────────────────────────
    fugas_aceite_combustible = models.CharField(max_length=20, choices=EstadoGeneral.choices, blank=True, verbose_name='Fugas aceite/combustible')
    nivel_combustible        = models.CharField(max_length=20, choices=EstadoGeneral.choices, blank=True, verbose_name='Nivel combustible')
    tipo_radiador            = models.CharField(max_length=100, blank=True, verbose_name='Tipo de radiador')
    nivel_agua_radiador      = models.CharField(max_length=20, choices=EstadoGeneral.choices, blank=True, verbose_name='Nivel agua radiador')
    nivel_aceite             = models.CharField(max_length=20, choices=EstadoGeneral.choices, blank=True, verbose_name='Nivel de aceite')
    horas_funcionamiento     = models.DecimalField(max_digits=10, decimal_places=1, null=True, blank=True, verbose_name='Horas de funcionamiento')
    obstruccion              = models.CharField(max_length=20, choices=EstadoGeneral.choices, blank=True, verbose_name='Obstrucción')

    # ── Voltajes L-L (línea a línea) ─────────────────────────────────────────
    voltaje_l1l2 = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, verbose_name='Voltaje L1-L2')
    voltaje_l2l3 = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, verbose_name='Voltaje L2-L3')
    voltaje_l1l3 = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, verbose_name='Voltaje L1-L3')

    # ── Voltajes L-N (línea a neutro) ────────────────────────────────────────
    voltaje_l1n = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, verbose_name='Voltaje L1-N')
    voltaje_l2n = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, verbose_name='Voltaje L2-N')
    voltaje_l3n = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, verbose_name='Voltaje L3-N')

    # ── Amperajes ────────────────────────────────────────────────────────────
    amperaje_a1 = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, verbose_name='Amperaje A1')
    amperaje_a2 = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, verbose_name='Amperaje A2')
    amperaje_a3 = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, verbose_name='Amperaje A3')

    # ── Lectura de datos ─────────────────────────────────────────────────────
    voltaje_generador  = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, verbose_name='Voltaje generador')
    frecuencia_hz      = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='Frecuencia (Hz)')
    rpm                = models.PositiveIntegerField(null=True, blank=True, verbose_name='RPM')
    voltaje_dc_cargador= models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, verbose_name='Voltaje DC cargador')

    # ── Arranque / Prueba de transferencia ───────────────────────────────────
    arranque_vacio             = models.CharField(max_length=20, choices=EstadoGeneral.choices, blank=True, verbose_name='Arranque en vacío')
    prueba_transferencia_carga = models.CharField(max_length=20, choices=EstadoGeneral.choices, blank=True, verbose_name='Prueba transferencia con carga')

    # ── Observaciones ────────────────────────────────────────────────────────
    observaciones = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Registro de Revisión Planta'
        verbose_name_plural = 'Registros de Revisión Plantas'
        ordering = ['-fecha', '-hora_inicio']

    def __str__(self):
        return f'Rev. {self.planta.id_qr} — {self.fecha}'

    def marcar_cerrado(self):
        self.cerrado = True
        self.save(update_fields=['cerrado', 'hora_fin'])

    @property
    def duracion_minutos(self):
        if self.hora_fin and self.hora_inicio:
            return round((self.hora_fin - self.hora_inicio).total_seconds() / 60)
        return None
