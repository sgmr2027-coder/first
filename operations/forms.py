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


CHOICES_SI_NO = [('si', 'Sí'), ('no', 'No')]


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
    # Usamos ChoiceField para poder detectar si no se seleccionó nada ('—')
    return _choice_field(label, CHOICES_SI_NO)


class ParametrosEntradaForm(forms.Form):
    """
    Check-in: corriente por compresor (según rack) + presiones + inspección detallada.
    """
    # Presiones fijas
    presion_succion_media = forms.DecimalField(
        label='Presión succión media temperatura (psi)',
        required=False,
        min_value=0,
        max_digits=6,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'data-label': 'Presión succión media'})
    )
    presion_succion_baja = forms.DecimalField(
        label='Presión succión baja temperatura (psi)',
        required=False,
        min_value=0,
        max_digits=6,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'data-label': 'Presión succión baja'})
    )
    presion_descarga = forms.DecimalField(
        label='Presión descarga (psi)',
        required=False,
        min_value=0,
        max_digits=6,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'data-label': 'Presión descarga'})
    )
    presion_entrada_condensacion = forms.DecimalField(
        label='Presión entrada condensación (psi)',
        required=False,
        min_value=0,
        max_digits=6,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'data-label': 'Presión entrada condensación'})
    )
    presion_salida_condensacion = forms.DecimalField(
        label='Presión salida condensación (psi)',
        required=False,
        min_value=0,
        max_digits=6,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'data-label': 'Presión salida condensación'})
    )

    def __init__(self, *args, rack=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.rack = rack
        if rack:
            n = min(rack.total_compresores or 0, MAX_COMPRESORES)
            media = rack.compresores_media or 0
            for i in range(1, n + 1):
                etiqueta = '(media)' if i <= media else '(baja)'
                
                # Campos existentes
                self.fields[f'corriente_compresor_{i}'] = _corriente_field(i, etiqueta)
                
                # Nuevos campos de inspección
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
        """Helper para renderizar campos agrupados por compresor y temperatura."""
        if not self.rack:
            return {'media': [], 'baja': []}
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


class ParametrosSalidaForm(ParametrosEntradaForm):
    """Mismos campos que entrada para comparar al cierre."""
    pass


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
