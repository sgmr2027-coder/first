from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.contrib.auth.decorators import login_required
from users.mixins import TecnicoRequiredMixin
from users.models import Rol
from django.views import View
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.template.loader import get_template
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from xhtml2pdf import pisa
import io
import os


from inventory.models import Rack
from .models import RegistroActividad, TipoActividad
from .services import (
    tecnico_tiene_tarea_abierta,
    obtener_tarea_abierta,
    iniciar_actividad,
    duracion_minutos,
    es_duracion_sospechosa,
)
from .forms import ParametrosEntradaForm, ParametrosSalidaForm, CierreForm


class ScannerView(TecnicoRequiredMixin, View):
    """Pantalla que activa la cámara para leer el QR del rack."""
    def get(self, request):
        tarea_abierta = obtener_tarea_abierta(request.user)
        racks = Rack.objects.filter(activo=True).order_by('tienda__nombre', 'ubicacion')
        return render(request, 'operations/scanner.html', {
            'tarea_abierta': tarea_abierta,
            'racks': racks,
        })


class FichaTecnicaView(TecnicoRequiredMixin, View):
    """Ficha del rack + botones Preventivo / Correctivo / Emergencia."""
    def get(self, request, rack_id):
        rack = get_object_or_404(Rack, pk=rack_id, activo=True)
        if tecnico_tiene_tarea_abierta(request.user):
            tarea = obtener_tarea_abierta(request.user)
            if tarea.rack_id != rack.id:
                return render(request, 'operations/bloqueo_tarea.html', {
                    'tarea_abierta': tarea,
                    'rack_solicitado': rack,
                })
        return render(request, 'operations/ficha_tecnica.html', {
            'rack': rack,
            'tipos': TipoActividad.choices,
        })


class IniciarActividadView(TecnicoRequiredMixin, View):
    """POST: inicia cronómetro y crea registro; redirige a check-in."""
    def post(self, request, rack_id):
        rack = get_object_or_404(Rack, pk=rack_id, activo=True)
        tipo = request.POST.get('tipo_actividad')
        if not tipo:
            return redirect('operations:ficha', rack_id=rack_id)
        try:
            registro = iniciar_actividad(request.user, rack, tipo)
            return redirect('operations:checkin', registro_id=registro.pk)
        except ValueError as e:
            return render(request, 'operations/ficha_tecnica.html', {
                'rack': rack,
                'tipos': TipoActividad.choices,
                'error': str(e),
            })


class CheckInView(TecnicoRequiredMixin, View):
    """Parámetros de entrada. No se puede ver check-out hasta guardar."""
    def get(self, request, registro_id):
        registro = get_object_or_404(RegistroActividad, pk=registro_id, tecnico=request.user, cerrado=False)
        form = ParametrosEntradaForm(initial=registro.datos_entrada or None, rack=registro.rack)
        return render(request, 'operations/checkin.html', {
            'registro': registro,
            'form': form,
        })

    def post(self, request, registro_id):
        registro = get_object_or_404(RegistroActividad, pk=registro_id, tecnico=request.user, cerrado=False)
        form = ParametrosEntradaForm(request.POST, rack=registro.rack)
        if form.is_valid():
            registro.datos_entrada = form.to_json()
            registro.save(update_fields=['datos_entrada'])
            return redirect('operations:checkout', registro_id=registro.pk)
        return render(request, 'operations/checkin.html', {'registro': registro, 'form': form})


class SaltarCheckInView(TecnicoRequiredMixin, View):
    """POST: marca todos los parámetros iniciales como 'No medido' y redirige a cierre."""
    def post(self, request, registro_id):
        registro = get_object_or_404(RegistroActividad, pk=registro_id, tecnico=request.user, cerrado=False)
        form = ParametrosEntradaForm(rack=registro.rack)
        # Llenamos el JSON de entrada con "No medido" para cada campo del form
        datos = {}
        for field_name in form.fields:
            datos[field_name] = "No medido"
        registro.datos_entrada = datos
        registro.save(update_fields=['datos_entrada'])
        return redirect('operations:checkout', registro_id=registro.pk)


class CheckOutView(TecnicoRequiredMixin, View):
    """Cierre: mismos parámetros que entrada + observaciones. Al finalizar se graba hora_fin y se bloquea."""
    def get(self, request, registro_id):
        registro = get_object_or_404(RegistroActividad, pk=registro_id, tecnico=request.user, cerrado=False)
        form_salida = ParametrosSalidaForm(initial=registro.datos_salida or None, rack=registro.rack)
        form_cierre = CierreForm(initial={'observaciones': registro.observaciones})
        return render(request, 'operations/checkout.html', {
            'registro': registro,
            'form_salida': form_salida,
            'form_cierre': form_cierre,
        })

    def post(self, request, registro_id):
        registro = get_object_or_404(RegistroActividad, pk=registro_id, tecnico=request.user, cerrado=False)
        form_salida = ParametrosSalidaForm(request.POST, rack=registro.rack)
        form_cierre = CierreForm(request.POST)
        if form_salida.is_valid() and form_cierre.is_valid():
            registro.datos_salida = form_salida.to_json()
            registro.observaciones = form_cierre.cleaned_data.get('observaciones', '')
            registro.hora_fin = timezone.now()
            registro.marcar_cerrado()
            minutos = duracion_minutos(registro.hora_inicio, registro.hora_fin)
            alerta_corto = es_duracion_sospechosa(minutos)
            return render(request, 'operations/actividad_cerrada.html', {
                'registro': registro,
                'minutos': minutos,
                'alerta_corto': alerta_corto,
            })
        return render(request, 'operations/checkout.html', {
            'registro': registro,
            'form_salida': form_salida,
            'form_cierre': form_cierre,
        })


# API para el escáner QR (solo técnicos)
@require_GET
@login_required
def api_rack_qr(request, id_qr):
    """Devuelve JSON del rack. Solo técnicos (supervisores no escanean)."""
    if getattr(request.user, 'rol', None) != Rol.TECNICO:
        return JsonResponse({'ok': False, 'error': 'Solo técnicos pueden escanear.'}, status=403)
    rack = get_object_or_404(Rack, id_qr=id_qr, activo=True)
    return JsonResponse({
        'ok': True,
        'id': rack.pk,
        'id_qr': rack.id_qr,
        'tienda': rack.tienda.nombre,
        'marca': rack.marca,
        'ubicacion': rack.ubicacion,
        'compresores_media': rack.compresores_media,
        'compresores_baja': rack.compresores_baja,
    })


def link_callback(uri, rel):
    """
    Convierte URIs de static/media en rutas de archivos absolutas para que pisa las encuentre.
    """
    import os
    s_url = settings.STATIC_URL     # e.g., '/static/'
    m_url = settings.MEDIA_URL      # e.g., '/media/' or '/'

    # 1. Determinar el path relativo y el directorio base
    # PRIORIDAD: Estáticos primero para evitar que MEDIA_URL="/" capture todo
    path = None
    relative_path = None
    
    if uri.startswith(s_url):
        relative_path = uri.replace(s_url, "", 1).lstrip('/')
        # Buscar en STATICFILES_DIRS (desarrollo)
        if settings.STATICFILES_DIRS:
            for d in settings.STATICFILES_DIRS:
                trial = os.path.join(d, relative_path)
                if os.path.exists(trial):
                    path = trial
                    break
        # Si no, buscar en STATIC_ROOT (producción)
        if not path:
            path = os.path.join(settings.STATIC_ROOT, relative_path)
            
    elif m_url and uri.startswith(m_url):
        relative_path = uri.replace(m_url, "", 1).lstrip('/')
        path = os.path.join(settings.MEDIA_ROOT, relative_path)

    # Si encontramos una ruta física y es un archivo, retornarla
    if path and os.path.isfile(path):
        return path
    
    # Fallback por si la URI ya es una ruta absoluta o no se pudo resolver
    return uri


class IntervencionPDFView(View):
    """Genera el reporte PDF de la intervención técnica."""
    def get(self, request, registro_id):
        # Permitimos ver a técnicos y supervisores
        registro = get_object_or_404(RegistroActividad, pk=registro_id)
        
        # Preparar datos de compresores
        rack = registro.rack
        n_compresores = rack.total_compresores
        media_count = rack.compresores_media
        
        compresores_media = []
        compresores_baja = []
        
        # Sacamos los datos finales (datos_salida) si existen, si no, iniciales
        datos = registro.datos_salida if registro.datos_salida else registro.datos_entrada
        
        # Mapear detalles técnicos de compresores (modelo y serie)
        detalles_map = {c.numero: c for c in rack.detalles_compresores.all()}
        
        for i in range(1, n_compresores + 1):
            detalle = detalles_map.get(i)
            comp_data = {
                'numero': i,
                'modelo': detalle.modelo if detalle else '—',
                'serie': detalle.serie if detalle else '—',
                'corriente': datos.get(f'corriente_compresor_{i}', '—'),
                'estado_aceite': datos.get(f'estado_aceite_{i}', '—'),
                'nivel_aceite': datos.get(f'nivel_aceite_{i}', '—'),
                'ruido': datos.get(f'ruido_{i}', '—'),
                'dispara_aceite': datos.get(f'dispara_aceite_{i}', '—'),
                'dispara_presion': datos.get(f'dispara_presion_{i}', '—'),
                'funciona_traxoil': datos.get(f'funciona_traxoil_{i}', '—'),
            }
            if i <= media_count:
                compresores_media.append(comp_data)
            else:
                compresores_baja.append(comp_data)

        context = {
            'registro': registro,
            'rack': rack,
            'compresores_media': compresores_media,
            'compresores_baja': compresores_baja,
            'datos': datos,
            'fecha': registro.hora_fin or registro.hora_inicio,
        }

        # Mapeo de legibilidad para campos generales del Rack
        mapeo_rack = {
            'ajuste_refrigerante': {'si': 'SÍ', 'no': 'NO'},
            'condensador_limpio': {'limpio': 'LIMPIO', 'sucio': 'SUCIO'},
            'nivel_acumulador': {'alto': 'ALTO', 'medio': 'MEDIO', 'bajo': 'BAJO'},
            'ventiladores_condensadora': {
                'todos_ok': 'TODOS OPERATIVOS',
                'un_averiado': 'UN VENTILADOR AVERIADO',
                'varios_averiados': 'MÁS DE UN VENTILADOR AVERIADO'
            },
            'aislamiento_tuberias': {'bueno': 'BUENAS CONDICIONES', 'malo': 'MALAS CONDICIONES'},
            'valvulas_cierre': {'bueno': 'BUENAS CONDICIONES', 'malo': 'MALAS CONDICIONES'},
            'manifolds_recibidores': {'bueno': 'BUENAS CONDICIONES', 'malo': 'MALAS CONDICIONES'},
        }
        
        # Crear un diccionario con valores legibles
        readable = {}
        for key, val in datos.items():
            if key in mapeo_rack and val in mapeo_rack[key]:
                readable[key] = mapeo_rack[key][val]
            else:
                readable[key] = val
        
        context['readable'] = readable

        # Renderizar a PDF
        template = get_template('operations/reporte_pdf.html')
        html = template.render(context)
        
        result = io.BytesIO()
        pdf = pisa.pisaDocument(io.BytesIO(html.encode("UTF-8")), result, link_callback=link_callback)
        
        if not pdf.err:
            response = HttpResponse(result.getvalue(), content_type='application/pdf')
            filename = f"Reporte_{rack.id_qr}_{context['fecha'].strftime('%Y%m%d')}.pdf"
            response['Content-Disposition'] = f'inline; filename="{filename}"'
            return response
            
        return HttpResponse("Error al generar PDF", status=500)
