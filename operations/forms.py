"""
Formularios para parámetros de entrada (check-in) y salida (check-out).
Estructura compatible con datos_entrada / datos_salida JSON.
"""
from django import forms


def build_parametros_form(compresores_media=0, compresores_baja=0, prefix=''):
    """Construye campos dinámicos según cantidad de compresores (opcional para v1)."""
    # En v1 usamos campos fijos; luego se pueden generar por total_compresores
    return None


class ParametrosEntradaForm(forms.Form):
    """Check-in: presiones, temperaturas, setpoints, amperajes."""
    presion_succion = forms.DecimalField(
        label='Presión succión (psi)',
        required=False,
        min_value=0,
        max_digits=6,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    presion_descarga = forms.DecimalField(
        label='Presión descarga (psi)',
        required=False,
        min_value=0,
        max_digits=6,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    temp_succion = forms.DecimalField(
        label='Temp. succión (°C)',
        required=False,
        max_digits=5,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'})
    )
    temp_descarga = forms.DecimalField(
        label='Temp. descarga (°C)',
        required=False,
        max_digits=5,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'})
    )
    setpoint_actual = forms.DecimalField(
        label='Set-point actual (°C)',
        required=False,
        max_digits=5,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'})
    )
    amperaje_linea_1 = forms.DecimalField(
        label='Amperaje línea 1 (A)',
        required=False,
        min_value=0,
        max_digits=6,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    amperaje_linea_2 = forms.DecimalField(
        label='Amperaje línea 2 (A)',
        required=False,
        min_value=0,
        max_digits=6,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    amperaje_linea_3 = forms.DecimalField(
        label='Amperaje línea 3 (A)',
        required=False,
        min_value=0,
        max_digits=6,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    observaciones_entrada = forms.CharField(
        label='Notas de entrada',
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
    )

    def to_json(self):
        from decimal import Decimal
        data = {}
        for k, v in self.cleaned_data.items():
            if v is not None and v != '':
                if isinstance(v, Decimal):
                    data[k] = float(v)
                elif isinstance(v, (int, float)):
                    data[k] = v
                else:
                    data[k] = str(v)
        return data


class ParametrosSalidaForm(ParametrosEntradaForm):
    """Mismos campos que entrada para comparar resultados."""
    pass


class CierreForm(forms.Form):
    """Check-out: observaciones y parámetros finales."""
    observaciones = forms.CharField(
        label='Observaciones (ej: Cambio de compresor, Recarga de gas)',
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4})
    )
