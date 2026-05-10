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
 
from inventory.models import Rack, PlantaElectrica, RegistroPlanta
from .models import RegistroActividad, TipoActividad
from .services import (
    tecnico_tiene_tarea_abierta,
    obtener_tarea_abierta,
    iniciar_actividad,
    duracion_minutos,
    es_duracion_sospechosa,
)
from .forms import ParametrosEntradaForm, ParametrosSalidaForm, CierreForm
 
 
# ─────────────────────────────────────────────────────────────────────────────
# SCANNER UNIFICADO
# ─────────────────────────────────────────────────────────────────────────────
 
class ScannerView(TecnicoRequiredMixin, View):
    """Pantalla principal: elige tipo de equipo (Rack o Planta) y luego el equipo."""
    def get(self, request):
        tarea_abierta = obtener_tarea_abierta(request.user)
        return render(request, 'operations/scanner.html', {
            'tarea_abierta': tarea_abierta,
            'racks': Rack.objects.filter(activo=True).select_related('tienda').order_by('tienda__nombre', 'ubicacion'),
            'plantas': PlantaElectrica.objects.filter(activo=True).select_related('tienda').order_by('tienda__nombre', 'ubicacion'),
        })
 
 
# ─────────────────────────────────────────────────────────────────────────────
# RACK — Ficha e inicio de actividad
# ─────────────────────────────────────────────────────────────────────────────
 
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
 
 
# ─────────────────────────────────────────────────────────────────────────────
# RACK — Check-in / Check-out
# ─────────────────────────────────────────────────────────────────────────────
 
class CheckInView(TecnicoRequiredMixin, View):
    """Parámetros de entrada. No se puede ver check-out hasta guardar."""
    def get(self, request, registro_id):
        registro = get_object_or_404(RegistroActividad, pk=registro_id, tecnico=request.user, cerrado=False)
        form = ParametrosEntradaForm(initial=registro.datos_entrada or None, rack=registro.rack)
        return render(request, 'operations/checkin.html', {'registro': registro, 'form': form})
 
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
        datos = {field_name: 'No medido' for field_name in form.fields}
        registro.datos_entrada = datos
        registro.save(update_fields=['datos_entrada'])
        return redirect('operations:checkout', registro_id=registro.pk)
 
 
class CheckOutView(TecnicoRequiredMixin, View):
    """Cierre: mismos parámetros que entrada + observaciones."""
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
 
 
# ─────────────────────────────────────────────────────────────────────────────
# RACK — API QR
# ─────────────────────────────────────────────────────────────────────────────
 
@require_GET
@login_required
def api_rack_qr(request, id_qr):
    """Devuelve JSON del rack. Solo técnicos."""
    try:
        print(f"DEBUG: api_rack_qr recibida con id_qr='{id_qr}'")
        if getattr(request.user, 'rol', None) != Rol.TECNICO:
            return JsonResponse({'ok': False, 'error': 'Solo técnicos pueden escanear.'})
        
        # Búsqueda insensible a mayúsculas y sin espacios
        rack = Rack.objects.get(id_qr__iexact=id_qr.strip(), activo=True)
        
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
    except Rack.DoesNotExist:
        disponibles = list(Rack.objects.filter(activo=True).values_list('id_qr', flat=True)[:10])
        return JsonResponse({
            'ok': False, 
            'error': f'No se encontró "{id_qr}". Disponibles: {disponibles}'
        })
    except Exception as e:
        return JsonResponse({'ok': False, 'error': f'ERROR CRÍTICO: {str(e)}'})
 
 
# ─────────────────────────────────────────────────────────────────────────────
# PLANTA ELÉCTRICA — API QR
# ─────────────────────────────────────────────────────────────────────────────
 
@require_GET
@login_required
def api_planta_qr(request, id_qr):
    """Devuelve JSON de la planta eléctrica. Solo técnicos."""
    try:
        print(f"DEBUG: api_planta_qr recibida con id_qr='{id_qr}'")
        if getattr(request.user, 'rol', None) != Rol.TECNICO:
            return JsonResponse({'ok': False, 'error': 'Solo técnicos pueden escanear.'})
        
        planta = PlantaElectrica.objects.get(id_qr__iexact=id_qr.strip(), activo=True)
        
        return JsonResponse({
            'ok': True,
            'id': planta.pk,
            'id_qr': planta.id_qr,
            'tienda': planta.tienda.nombre,
            'marca': planta.marca,
            'modelo': planta.modelo,
            'capacidad_kva': str(planta.capacidad_kva) if planta.capacidad_kva else None,
            'ubicacion': planta.ubicacion,
        })
    except PlantaElectrica.DoesNotExist:
        disponibles = list(PlantaElectrica.objects.filter(activo=True).values_list('id_qr', flat=True)[:10])
        return JsonResponse({
            'ok': False, 
            'error': f'No se encontró "{id_qr}". Disponibles: {disponibles}'
        })
    except Exception as e:
        return JsonResponse({'ok': False, 'error': f'ERROR CRÍTICO: {str(e)}'})
 
 
# ─────────────────────────────────────────────────────────────────────────────
# PLANTA ELÉCTRICA — Ficha y registro de revisión
# ─────────────────────────────────────────────────────────────────────────────
 
class FichaPlantaView(TecnicoRequiredMixin, View):
    """Ficha de la planta + botón para iniciar revisión mensual."""
    def get(self, request, planta_id):
        planta = get_object_or_404(PlantaElectrica, pk=planta_id, activo=True)
        ultimo_registro = planta.registros.order_by('-fecha').first()
        return render(request, 'operations/ficha_planta.html', {
            'planta': planta,
            'ultimo_registro': ultimo_registro,
        })
 
 
class IniciarRevisionPlantaView(TecnicoRequiredMixin, View):
    """POST: crea un RegistroPlanta abierto y redirige al formulario de revisión."""
    def post(self, request, planta_id):
        planta = get_object_or_404(PlantaElectrica, pk=planta_id, activo=True)
        registro = RegistroPlanta.objects.create(
            planta=planta,
            tecnico=request.user,
            fecha=timezone.now().date(),
        )
        return redirect('operations:revision_planta', registro_id=registro.pk)
 
 
class RevisionPlantaView(TecnicoRequiredMixin, View):
    """Formulario completo de revisión mensual de planta eléctrica."""
    def get(self, request, registro_id):
        registro = get_object_or_404(RegistroPlanta, pk=registro_id, tecnico=request.user, cerrado=False)
        return render(request, 'operations/revision_planta.html', {'registro': registro})
 
    def post(self, request, registro_id):
        registro = get_object_or_404(RegistroPlanta, pk=registro_id, tecnico=request.user, cerrado=False)
 
        def dec(key):
            val = request.POST.get(key, '').strip()
            try:
                return float(val) if val else None
            except ValueError:
                return None
 
        def entero(key):
            val = request.POST.get(key, '').strip()
            try:
                return int(val) if val else None
            except ValueError:
                return None
 
        def choice(key):
            return request.POST.get(key, '').strip()
 
        # Batería
        registro.bateria_cantidad           = entero('bateria_cantidad')
        registro.bateria_modelo             = request.POST.get('bateria_modelo', '').strip()
        registro.bateria_fecha_instalacion  = request.POST.get('bateria_fecha_instalacion') or None
        registro.bateria_estado_cargador    = choice('bateria_estado_cargador')
        registro.bateria_nivel_carga        = choice('bateria_nivel_carga')
 
        # Fluidos
        registro.fugas_aceite_combustible   = choice('fugas_aceite_combustible')
        registro.nivel_combustible          = choice('nivel_combustible')
        registro.tipo_radiador              = request.POST.get('tipo_radiador', '').strip()
        registro.nivel_agua_radiador        = choice('nivel_agua_radiador')
        registro.nivel_aceite               = choice('nivel_aceite')
        registro.horas_funcionamiento       = dec('horas_funcionamiento')
        registro.obstruccion                = choice('obstruccion')
 
        # Voltajes L-L
        registro.voltaje_l1l2 = dec('voltaje_l1l2')
        registro.voltaje_l2l3 = dec('voltaje_l2l3')
        registro.voltaje_l1l3 = dec('voltaje_l1l3')
 
        # Voltajes L-N
        registro.voltaje_l1n = dec('voltaje_l1n')
        registro.voltaje_l2n = dec('voltaje_l2n')
        registro.voltaje_l3n = dec('voltaje_l3n')
 
        # Amperajes
        registro.amperaje_a1 = dec('amperaje_a1')
        registro.amperaje_a2 = dec('amperaje_a2')
        registro.amperaje_a3 = dec('amperaje_a3')
 
        # Lectura de datos
        registro.voltaje_generador   = dec('voltaje_generador')
        registro.frecuencia_hz       = dec('frecuencia_hz')
        registro.rpm                 = entero('rpm')
        registro.voltaje_dc_cargador = dec('voltaje_dc_cargador')
 
        # Arranque / transferencia
        registro.arranque_vacio             = choice('arranque_vacio')
        registro.prueba_transferencia_carga = choice('prueba_transferencia_carga')
 
        # Cierre
        registro.observaciones = request.POST.get('observaciones', '').strip()
        registro.hora_fin = timezone.now()
        registro.marcar_cerrado()
 
        return redirect('operations:pdf_planta', registro_id=registro.pk)
 
 
# ─────────────────────────────────────────────────────────────────────────────
# PDF — helper link_callback (compartido)
# ─────────────────────────────────────────────────────────────────────────────
 
def link_callback(uri, rel):
    """
    Convierte URIs de static/media en rutas absolutas para xhtml2pdf.
    """
    import os
    from django.conf import settings
    from django.contrib.staticfiles import finders

    # 1. Intentar resolver con finders (especialmente útil en desarrollo y para assets estáticos)
    clean_uri = uri.replace(settings.STATIC_URL, "")
    result = finders.find(clean_uri)
    if result:
        return result

    # 2. Fallback manual para STATIC_ROOT y MEDIA_ROOT
    path = None
    if uri.startswith(settings.STATIC_URL):
        relative_path = uri.replace(settings.STATIC_URL, "", 1).lstrip('/')
        path = os.path.join(settings.STATIC_ROOT, relative_path)
    elif settings.MEDIA_URL and uri.startswith(settings.MEDIA_URL):
        relative_path = uri.replace(settings.MEDIA_URL, "", 1).lstrip('/')
        path = os.path.join(settings.MEDIA_ROOT, relative_path)

    if path and os.path.isfile(path):
        return path
    
    return uri
 
 
# ─────────────────────────────────────────────────────────────────────────────
# PDF — Rack
# ─────────────────────────────────────────────────────────────────────────────
 
class IntervencionPDFView(View):
    """Genera el reporte PDF de la intervención técnica de un rack."""
    def get(self, request, registro_id):
        registro = get_object_or_404(RegistroActividad, pk=registro_id)
        rack = registro.rack
        datos = registro.datos_salida if registro.datos_salida else registro.datos_entrada
 
        detalles_map = {c.numero: c for c in rack.detalles_compresores.all()}
        compresores_media, compresores_baja = [], []
 
        for i in range(1, rack.total_compresores + 1):
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
            if i <= rack.compresores_media:
                compresores_media.append(comp_data)
            else:
                compresores_baja.append(comp_data)
 
        mapeo_rack = {
            'ajuste_refrigerante':       {'si': 'SÍ', 'no': 'NO'},
            'condensador_limpio':        {'limpio': 'LIMPIO', 'sucio': 'SUCIO'},
            'nivel_acumulador':          {'alto': 'ALTO', 'medio': 'MEDIO', 'bajo': 'BAJO'},
            'ventiladores_condensadora': {
                'todos_ok': 'TODOS OPERATIVOS',
                'un_averiado': 'UN VENTILADOR AVERIADO',
                'varios_averiados': 'MÁS DE UN VENTILADOR AVERIADO',
            },
            'aislamiento_tuberias': {'bueno': 'BUENAS CONDICIONES', 'malo': 'MALAS CONDICIONES'},
            'valvulas_cierre':      {'bueno': 'BUENAS CONDICIONES', 'malo': 'MALAS CONDICIONES'},
            'manifolds_recibidores':{'bueno': 'BUENAS CONDICIONES', 'malo': 'MALAS CONDICIONES'},
        }
        readable = {
            key: mapeo_rack[key].get(val, val) if key in mapeo_rack else val
            for key, val in datos.items()
        }
 
        context = {
            'registro': registro,
            'rack': rack,
            'compresores_media': compresores_media,
            'compresores_baja': compresores_baja,
            'datos': datos,
            'readable': readable,
            'fecha': registro.hora_fin or registro.hora_inicio,
        }
 
        template = get_template('operations/reporte_pdf.html')
        html = template.render(context)
        result = io.BytesIO()
        pdf = pisa.pisaDocument(io.BytesIO(html.encode('UTF-8')), result, link_callback=link_callback)
 
        if not pdf.err:
            response = HttpResponse(result.getvalue(), content_type='application/pdf')
            filename = f"Reporte_{rack.id_qr}_{context['fecha'].strftime('%Y%m%d')}.pdf"
            response['Content-Disposition'] = f'inline; filename="{filename}"'
            return response
        return HttpResponse('Error al generar PDF', status=500)
 
 
# ─────────────────────────────────────────────────────────────────────────────
# PDF — Planta Eléctrica
# ─────────────────────────────────────────────────────────────────────────────
 
class PlantaPDFView(View):
    """Genera el reporte PDF de la revisión mensual de una planta eléctrica."""
    def get(self, request, registro_id):
        registro = get_object_or_404(RegistroPlanta, pk=registro_id)
        planta = registro.planta
 
        ESTADO_LABELS = {'bueno': 'Bueno', 'regular': 'Regular', 'malo': 'Malo', 'na': 'N/A', '': '—'}
        lbl = lambda v: ESTADO_LABELS.get(v, v or '—')
 
        context = {
            'registro': registro,
            'planta': planta,
            'fecha': registro.fecha,
            'fugas':                  lbl(registro.fugas_aceite_combustible),
            'nivel_combustible':      lbl(registro.nivel_combustible),
            'bateria_estado_cargador':lbl(registro.bateria_estado_cargador),
            'bateria_nivel_carga':    lbl(registro.bateria_nivel_carga),
            'nivel_agua_radiador':    lbl(registro.nivel_agua_radiador),
            'nivel_aceite':           lbl(registro.nivel_aceite),
            'obstruccion':            lbl(registro.obstruccion),
            'arranque_vacio':         lbl(registro.arranque_vacio),
            'prueba_transferencia':   lbl(registro.prueba_transferencia_carga),
        }
 
        template = get_template('operations/reporte_pdf_planta.html')
        html = template.render(context)
        result = io.BytesIO()
        pdf = pisa.pisaDocument(io.BytesIO(html.encode('UTF-8')), result, link_callback=link_callback)
 
        if not pdf.err:
            response = HttpResponse(result.getvalue(), content_type='application/pdf')
            filename = f"Planta_{planta.id_qr}_{registro.fecha}.pdf"
            response['Content-Disposition'] = f'inline; filename="{filename}"'
            return response
        return HttpResponse('Error al generar PDF', status=500)