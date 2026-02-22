"""
Formularios para parámetros de entrada (check-in) y salida (check-out).
Corriente por compresor según rack; presiones fijas. Estructura en datos_entrada/datos_salida JSON.
"""
from django import forms

MAX_COMPRESORES = 24  # límite para no generar demasiados campos


# Opciones para inspección de compresores
CHOICES_ACEITE_ESTADO = [('limpio', 'Limpio'), ('sucio', 'Sucio')]
CHOICES_ACEITE_NIVEL = [('bajo', 'Bajo'), ('medio', 'Medio'), ('normal', 'Normal')]
CHOICES_RUIDO = [('bajo', 'Bajo'), ('medio', 'Medio'), ('alto', 'Alto')]
CHOICES_SI_NO = [('si', 'Sí'), ('no', 'No')]

# Opciones para inspección general del Rack
CHOICES_NIVEL_RA = [('alto', 'Alto'), ('medio', 'Medio'), ('bajo', 'Bajo')]
CHOICES_LIMPIEZA = [('limpio', 'Limpio'), ('sucio', 'Sucio')]
CHOICES_VENTILADORES = [
    ('todos_ok', 'Todos operativos'), 
    ('un_averiado', 'Un ventilador averiado'), 
    ('varios_averiados', 'Más de un ventilador averiado')
]
CHOICES_CONDICIONES = [('bueno', 'Buenas condiciones'), ('malo', 'Malas condiciones')]


def _corriente_field(numero, etiqueta_extra=''):
    """Campo de corriente (A) para un compresor."""
    label = f'Corriente {numero} {etiqueta_extra}'
    return forms.DecimalField(
        label=label,
        required=False,
        min_value=0,
        max_digits=6,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 
            'step': '0.01', 
            'placeholder': 'A',
            'data-label': label
        })
    )


def _choice_field(label, choices):
    return forms.ChoiceField(
        label=label,
        choices=[('', '—')] + choices,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select form-select-sm',
            'data-label': label
        })
    )


def _boolean_field(label):
    return _choice_field(label, CHOICES_SI_NO)


class ParametrosEntradaForm(forms.Form):
    """
    Check-in SIMPLIFICADO: Solo corriente por compresor.
    """
    def __init__(self, *args, rack=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.rack = rack
        if rack:
            n = min(rack.total_compresores or 0, MAX_COMPRESORES)
            media = rack.compresores_media or 0
            for i in range(1, n + 1):
                etiqueta = '(media)' if i <= media else '(baja)'
                self.fields[f'corriente_compresor_{i}'] = _corriente_field(i, etiqueta)

    def to_json(self):
        from decimal import Decimal
        data = {}
        for k, v in self.cleaned_data.items():
            if v is True or v is False:
                data[k] = v
            elif v is not None and v != '':
                if isinstance(v, Decimal):
                    data[k] = float(v)
                elif isinstance(v, (int, float)):
                    data[k] = v
                else:
                    data[k] = str(v)
        return data

    def get_compresores(self):
        """Helper para renderizar campos en el template (solo corriente en check-in)."""
        if not self.rack:
            return {'media': [], 'baja': []}
        groups = {'media': [], 'baja': []}
        n = min(self.rack.total_compresores or 0, MAX_COMPRESORES)
        media_count = self.rack.compresores_media or 0
        for i in range(1, n + 1):
            temp_key = 'media' if i <= media_count else 'baja'
            groups[temp_key].append({
                'numero': i,
                'corriente': self.get(f'corriente_compresor_{i}'),
            })
        return groups
    
    def get(self, field_name):
        return self[field_name] if field_name in self.fields else None


class ParametrosSalidaForm(forms.Form):
    """
    Check-out COMPLETO: Amperajes + Presiones + Inspección Detallada + Estado General Rack.
    """
    # Presiones
    presion_succion_media = forms.DecimalField(label='Presión succión media', required=False, min_value=0, max_digits=6, decimal_places=2, widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    presion_succion_baja = forms.DecimalField(label='Presión succión baja', required=False, min_value=0, max_digits=6, decimal_places=2, widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    presion_descarga = forms.DecimalField(label='Presión descarga', required=False, min_value=0, max_digits=6, decimal_places=2, widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    presion_entrada_condensacion = forms.DecimalField(label='Entrada cond.', required=False, min_value=0, max_digits=6, decimal_places=2, widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    presion_salida_condensacion = forms.DecimalField(label='Salida cond.', required=False, min_value=0, max_digits=6, decimal_places=2, widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))

    # Inspección de componentes del Rack
    nivel_acumulador = _choice_field('Nivel acumulador refrigerante', CHOICES_NIVEL_RA)
    ajuste_refrigerante = _boolean_field('Realizó ajuste de refrigerante')
    condensador_limpio = _choice_field('Estado condensador del rack', CHOICES_LIMPIEZA)
    ventiladores_condensadora = _choice_field('Estado ventiladores condensadora', CHOICES_VENTILADORES)
    aislamiento_tuberias = _choice_field('Estado aislamiento de tuberías', CHOICES_CONDICIONES)
    valvulas_cierre = _choice_field('Estado válvulas de cierre', CHOICES_CONDICIONES)
    manifolds_recibidores = _choice_field('Manifolds y recibidores', CHOICES_CONDICIONES)

    def __init__(self, *args, rack=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.rack = rack
        if rack:
            n = min(rack.total_compresores or 0, MAX_COMPRESORES)
            media = rack.compresores_media or 0
            for i in range(1, n + 1):
                etiqueta = '(media)' if i <= media else '(baja)'
                self.fields[f'corriente_compresor_{i}'] = _corriente_field(i, etiqueta)
                self.fields[f'estado_aceite_{i}'] = _choice_field(f'Aceite C{i}', CHOICES_ACEITE_ESTADO)
                self.fields[f'nivel_aceite_{i}'] = _choice_field(f'Nivel C{i}', CHOICES_ACEITE_NIVEL)
                self.fields[f'ruido_{i}'] = _choice_field(f'Ruido C{i}', CHOICES_RUIDO)
                self.fields[f'dispara_aceite_{i}'] = _boolean_field(f'Disc. Aceite C{i}')
                self.fields[f'dispara_presion_{i}'] = _boolean_field(f'Disc. Presión C{i}')
                self.fields[f'funciona_traxoil_{i}'] = _boolean_field(f'Traxoil C{i}')

    def to_json(self):
        from decimal import Decimal
        data = {}
        for k, v in self.cleaned_data.items():
            if v is not None and v != '':
                if isinstance(v, Decimal): data[k] = float(v)
                elif isinstance(v, (int, float, bool)): data[k] = v
                else: data[k] = str(v)
        return data

    def get_compresores(self):
        if not self.rack: return {'media': [], 'baja': []}
        groups = {'media': [], 'baja': []}
        n = min(self.rack.total_compresores or 0, MAX_COMPRESORES)
        media_count = self.rack.compresores_media or 0
        for i in range(1, n + 1):
            temp_key = 'media' if i <= media_count else 'baja'
            groups[temp_key].append({
                'numero': i,
                'corriente': self[f'corriente_compresor_{i}'],
                'estado_aceite': self[f'estado_aceite_{i}'],
                'nivel_aceite': self[f'nivel_aceite_{i}'],
                'ruido': self[f'ruido_{i}'],
                'dispara_aceite': self[f'dispara_aceite_{i}'],
                'dispara_presion': self[f'dispara_presion_{i}'],
                'funciona_traxoil': self[f'funciona_traxoil_{i}'],
            })
        return groups


class CierreForm(forms.Form):
    """Check-out: observación del trabajo realizado."""
    observaciones = forms.CharField(
        label='Observaciones del trabajo realizado',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Ej: Cambio de compresor, recarga de gas, ajuste de presiones...'
        })
    )
