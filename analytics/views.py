import csv
from datetime import datetime
from io import StringIO
from itertools import chain

from django.db.models import Avg, F, ExpressionWrapper, DurationField, Count, Q
from django.http import HttpResponse
from django.utils import timezone
from django.views.generic import TemplateView, View

from users.mixins import SupervisorRequiredMixin
from inventory.models import Tienda, Rack, PlantaElectrica, RegistroPlanta, Zona, AsignacionTecnico, Especialidad
from operations.models import RegistroActividad, TipoActividad


def _get_cerrados_merged(request):
    """Obtiene y une los registros cerrados de Racks y Plantas aplicándoles filtros."""
    tienda_id = request.GET.get('tienda', '').strip()
    fecha_inicio_str = request.GET.get('fecha_inicio', '').strip()
    fecha_fin_str = request.GET.get('fecha_fin', '').strip()
    tipo_activo = request.GET.get('tipo_activo', 'todos')
    
    fecha_inicio = None
    fecha_fin = None
    try:
        if fecha_inicio_str:
            fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
        if fecha_fin_str:
            fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
    except ValueError:
        pass

    qs_racks = RegistroActividad.objects.none()
    qs_plantas = RegistroPlanta.objects.none()

    if tipo_activo in ['todos', 'racks']:
        qs_racks = RegistroActividad.objects.all().select_related('rack', 'rack__tienda', 'tecnico')
        if tienda_id:
            qs_racks = qs_racks.filter(rack__tienda_id=tienda_id)
        if fecha_inicio:
            qs_racks = qs_racks.filter(hora_inicio__date__gte=fecha_inicio)
        if fecha_fin:
            qs_racks = qs_racks.filter(hora_inicio__date__lte=fecha_fin)
        
        # Marcamos el tipo para el template
        for r in qs_racks: r.tipo_equipo = 'Rack'

    if tipo_activo in ['todos', 'plantas']:
        qs_plantas = RegistroPlanta.objects.all().select_related('planta', 'planta__tienda', 'tecnico')
        if tienda_id:
            qs_plantas = qs_plantas.filter(planta__tienda_id=tienda_id)
        if fecha_inicio:
            qs_plantas = qs_plantas.filter(hora_inicio__date__gte=fecha_inicio)
        if fecha_fin:
            qs_plantas = qs_plantas.filter(hora_inicio__date__lte=fecha_fin)
            
        # Marcamos el tipo para el template
        for p in qs_plantas: p.tipo_equipo = 'Planta'

    merged = sorted(
        chain(qs_racks, qs_plantas),
        key=lambda x: x.hora_inicio,
        reverse=True
    )
    return merged


def _pct(subset, total):
    """% de tiendas en `total` que están también en `subset`."""
    total = total or set()
    if not total:
        return None
    return round(len(subset & total) / len(total) * 100, 1)


def _calcular_cobertura_preventivos(fecha_inicio, fecha_fin, tienda_id=None):
    """
    Calcula el % de puntos de venta (Tiendas) con preventivo realizado,
    separado en Racks y Plantas, en total, por zona y por técnico
    (según las asignaciones definidas en AsignacionTecnico).
    """
    # Universo de tiendas que SÍ tienen el activo instalado (racks/plantas activos)
    racks_activos_qs = Rack.objects.filter(activo=True)
    plantas_activas_qs = PlantaElectrica.objects.filter(activo=True)
    if tienda_id:
        racks_activos_qs = racks_activos_qs.filter(tienda_id=tienda_id)
        plantas_activas_qs = plantas_activas_qs.filter(tienda_id=tienda_id)

    tiendas_con_racks = set(racks_activos_qs.values_list('tienda_id', flat=True))
    tiendas_con_plantas = set(plantas_activas_qs.values_list('tienda_id', flat=True))

    # Preventivos realizados en el rango de fechas
    prev_racks_qs = RegistroActividad.objects.filter(tipo_actividad=TipoActividad.PREVENTIVO)
    prev_plantas_qs = RegistroPlanta.objects.all()
    if fecha_inicio:
        prev_racks_qs = prev_racks_qs.filter(hora_inicio__date__gte=fecha_inicio)
        prev_plantas_qs = prev_plantas_qs.filter(hora_inicio__date__gte=fecha_inicio)
    if fecha_fin:
        prev_racks_qs = prev_racks_qs.filter(hora_inicio__date__lte=fecha_fin)
        prev_plantas_qs = prev_plantas_qs.filter(hora_inicio__date__lte=fecha_fin)
    if tienda_id:
        prev_racks_qs = prev_racks_qs.filter(rack__tienda_id=tienda_id)
        prev_plantas_qs = prev_plantas_qs.filter(planta__tienda_id=tienda_id)

    hechos_racks = set(prev_racks_qs.values_list('rack__tienda_id', 'tecnico_id'))
    hechos_plantas = set(prev_plantas_qs.values_list('planta__tienda_id', 'tecnico_id'))

    tiendas_hechas_racks = {t for t, _ in hechos_racks}
    tiendas_hechas_plantas = {t for t, _ in hechos_plantas}

    # ── Total general ────────────────────────────────────────────────────
    cobertura_global = {
        'racks': {
            'total': len(tiendas_con_racks),
            'hechos': len(tiendas_hechas_racks & tiendas_con_racks),
            'pct': _pct(tiendas_hechas_racks, tiendas_con_racks),
        },
        'plantas': {
            'total': len(tiendas_con_plantas),
            'hechos': len(tiendas_hechas_plantas & tiendas_con_plantas),
            'pct': _pct(tiendas_hechas_plantas, tiendas_con_plantas),
        },
    }

    # ── Por zona ─────────────────────────────────────────────────────────
    tiendas_all = Tienda.objects.all()
    if tienda_id:
        tiendas_all = tiendas_all.filter(pk=tienda_id)

    tiendas_por_zona = {}
    zona_nombres = {}
    for t in tiendas_all.select_related('zona').only('id', 'zona__id', 'zona__nombre'):
        zona_id = t.zona_id
        tiendas_por_zona.setdefault(zona_id, set()).add(t.id)
        zona_nombres[zona_id] = t.zona.nombre if t.zona_id else 'Sin zona asignada'

    cobertura_por_zona = []
    for zona_id, tienda_ids_zona in sorted(
        tiendas_por_zona.items(),
        key=lambda kv: (kv[0] is None, zona_nombres.get(kv[0], ''))
    ):
        racks_total_z = tienda_ids_zona & tiendas_con_racks
        plantas_total_z = tienda_ids_zona & tiendas_con_plantas
        if not racks_total_z and not plantas_total_z:
            continue
        cobertura_por_zona.append({
            'zona': zona_nombres.get(zona_id, 'Sin zona asignada'),
            'racks_total': len(racks_total_z),
            'racks_hechos': len(tiendas_hechas_racks & racks_total_z),
            'racks_pct': _pct(tiendas_hechas_racks, racks_total_z),
            'plantas_total': len(plantas_total_z),
            'plantas_hechos': len(tiendas_hechas_plantas & plantas_total_z),
            'plantas_pct': _pct(tiendas_hechas_plantas, plantas_total_z),
        })

    # ── Por técnico (según asignaciones de preventivos) ─────────────────
    asignaciones = (
        AsignacionTecnico.objects
        .filter(activo=True)
        .select_related('tecnico')
    )
    if tienda_id:
        asignaciones = asignaciones.filter(tienda_id=tienda_id)

    tecnicos_map = {}
    for a in asignaciones:
        entry = tecnicos_map.setdefault(
            a.tecnico_id, {'tecnico': a.tecnico, 'racks': set(), 'plantas': set()}
        )
        if a.especialidad == Especialidad.RACKS:
            entry['racks'].add(a.tienda_id)
        else:
            entry['plantas'].add(a.tienda_id)

    cobertura_por_tecnico = []
    for tecnico_id, data in tecnicos_map.items():
        racks_asignadas = data['racks']
        plantas_asignadas = data['plantas']

        racks_hechas_tec = {t for (t, tec) in hechos_racks if tec == tecnico_id} & racks_asignadas
        plantas_hechas_tec = {t for (t, tec) in hechos_plantas if tec == tecnico_id} & plantas_asignadas

        cobertura_por_tecnico.append({
            'tecnico': data['tecnico'],
            'racks_total': len(racks_asignadas),
            'racks_hechos': len(racks_hechas_tec),
            'racks_pct': round(len(racks_hechas_tec) / len(racks_asignadas) * 100, 1) if racks_asignadas else None,
            'plantas_total': len(plantas_asignadas),
            'plantas_hechos': len(plantas_hechas_tec),
            'plantas_pct': round(len(plantas_hechas_tec) / len(plantas_asignadas) * 100, 1) if plantas_asignadas else None,
        })

    cobertura_por_tecnico.sort(
        key=lambda d: (d['tecnico'].nombre_completo or d['tecnico'].username).lower()
    )

    return {
        'cobertura_global': cobertura_global,
        'cobertura_por_zona': cobertura_por_zona,
        'cobertura_por_tecnico': cobertura_por_tecnico,
    }


class DashboardView(SupervisorRequiredMixin, TemplateView):
    """Dashboard premium: Visitas totales, MTTR, filtros y soporte para Racks y Plantas."""
    template_name = 'analytics/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request

        # Filtros (GET)
        tienda_id = request.GET.get('tienda', '').strip()
        fecha_inicio_str = request.GET.get('fecha_inicio', '').strip()
        fecha_fin_str = request.GET.get('fecha_fin', '').strip()
        tipo_activo = request.GET.get('tipo_activo', 'todos')
        
        fecha_inicio = None
        fecha_fin = None
        try:
            if fecha_inicio_str:
                fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
            if fecha_fin_str:
                fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
        except ValueError:
            pass

        # Querysets
        racks_qs = RegistroActividad.objects.all()
        plantas_qs = RegistroPlanta.objects.all()

        if tienda_id:
            racks_qs = racks_qs.filter(rack__tienda_id=tienda_id)
            plantas_qs = plantas_qs.filter(planta__tienda_id=tienda_id)
        
        if fecha_inicio:
            racks_qs = racks_qs.filter(hora_inicio__date__gte=fecha_inicio)
            plantas_qs = plantas_qs.filter(hora_inicio__date__gte=fecha_inicio)
        if fecha_fin:
            racks_qs = racks_qs.filter(hora_inicio__date__lte=fecha_fin)
            plantas_qs = plantas_qs.filter(hora_inicio__date__lte=fecha_fin)
            
        if tipo_activo == 'racks':
            plantas_qs = plantas_qs.none()
        elif tipo_activo == 'plantas':
            racks_qs = racks_qs.none()

        # Conteos
        conteo_racks = racks_qs.count()
        conteo_plantas = plantas_qs.count()
        context['visitas_conteo'] = conteo_racks + conteo_plantas
        
        if tipo_activo == 'racks':
            context['titulo_contador'] = 'Visitas Totales (Racks)'
        elif tipo_activo == 'plantas':
            context['titulo_contador'] = 'Visitas Totales (Plantas)'
        else:
            context['titulo_contador'] = 'Visitas Totales (Racks + Plantas)'

        # MTTR (Unificado)
        duracion_expr = ExpressionWrapper(F('hora_fin') - F('hora_inicio'), output_field=DurationField())
        
        racks_cerrados = racks_qs.filter(cerrado=True, hora_fin__isnull=False).annotate(dur=duracion_expr)
        plantas_cerradas = plantas_qs.filter(cerrado=True, hora_fin__isnull=False).annotate(dur=duracion_expr)
        
        total_minutos = 0
        total_cerrados = 0
        
        for r in racks_cerrados:
            if r.dur:
                total_minutos += r.dur.total_seconds() / 60
                total_cerrados += 1
        for p in plantas_cerradas:
            if p.dur:
                total_minutos += p.dur.total_seconds() / 60
                total_cerrados += 1
        
        context['mttr_minutos'] = round(total_minutos / total_cerrados, 1) if total_cerrados > 0 else None

        # Historial unificado
        context['historial'] = _get_cerrados_merged(request)[:100]

        # Cobertura de preventivos (% PDVs con preventivo — Racks / Plantas)
        cobertura = _calcular_cobertura_preventivos(
            fecha_inicio, fecha_fin, tienda_id or None
        )
        context['cobertura_global'] = cobertura['cobertura_global']
        context['cobertura_por_zona'] = cobertura['cobertura_por_zona']
        context['cobertura_por_tecnico'] = cobertura['cobertura_por_tecnico']

        # Contexto para selectores
        tiendas = list(Tienda.objects.all().order_by('nombre'))
        for t in tiendas: t.pk_str = str(t.pk)
        context['tiendas'] = tiendas
        
        context['tienda_seleccionada'] = tienda_id
        context['fecha_inicio_seleccionada'] = fecha_inicio_str
        context['fecha_fin_seleccionada'] = fecha_fin_str
        context['tipo_activo_seleccionado'] = tipo_activo
        return context


class ExportReportesView(SupervisorRequiredMixin, View):
    """Exporta el historial unificado en CSV."""
    def get(self, request):
        registros = _get_cerrados_merged(request)
        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow(['Fecha / Hora inicio', 'Técnico', 'Equipo', 'Tienda', 'Tipo Equipo', 'Tipo Actividad', 'Estado', 'Duración (min)'])
        
        for r in registros:
            tecnico = (r.tecnico.get_full_name() or r.tecnico.username) if r.tecnico else '—'
            es_rack = getattr(r, 'tipo_equipo', '') == 'Rack'
            
            equipo = r.rack.id_qr if es_rack else r.planta.id_qr
            tienda = r.rack.tienda.nombre if es_rack else r.planta.tienda.nombre
            tipo_act = r.get_tipo_actividad_display() if es_rack else 'Revisión Mensual'
            
            # Manejo seguro del método duracion_minutos vs la property duracion_minutos
            # RegistroActividad usa un método en _models.py o un helper? 
            # Ivan usó @property def duracion_minutos en RegistroPlanta!
            # Mientras que en RegistroActividad era un método o no existía.
            if es_rack:
                dur = r.duracion_minutos() if hasattr(r.duracion_minutos, '__call__') else r.duracion_minutos
            else:
                dur = r.duracion_minutos
                
            writer.writerow([
                r.hora_inicio.strftime('%d/%m/%Y %H:%M') if r.hora_inicio else '',
                tecnico,
                equipo,
                tienda,
                r.tipo_equipo,
                tipo_act,
                'Cerrado' if r.cerrado else 'Abierto',
                dur if r.hora_fin else '—',
            ])
            
        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="reporte_unificado_sgmr.csv"'
        return response
