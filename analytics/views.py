import csv
from datetime import datetime
from io import StringIO
from itertools import chain

from django.db.models import Avg, F, ExpressionWrapper, DurationField
from django.http import HttpResponse
from django.utils import timezone
from django.views.generic import TemplateView, View

from users.mixins import SupervisorRequiredMixin
from inventory.models import Tienda, Rack, PlantaElectrica, RegistroPlanta
from operations.models import RegistroActividad


def _get_cerrados_merged(request):
    """Obtiene y une los registros cerrados de Racks y Plantas aplicándoles filtros."""
    tienda_id = request.GET.get('tienda', '').strip()
    fecha_inicio_str = request.GET.get('fecha_inicio', '').strip()
    fecha_fin_str = request.GET.get('fecha_fin', '').strip()
    
    fecha_inicio = None
    fecha_fin = None
    try:
        if fecha_inicio_str:
            fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
        if fecha_fin_str:
            fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
    except ValueError:
        pass

    # Racks
    qs_racks = RegistroActividad.objects.all().select_related('rack', 'rack__tienda', 'tecnico')
    # Plantas
    qs_plantas = RegistroPlanta.objects.all().select_related('planta', 'planta__tienda', 'tecnico')

    if tienda_id:
        qs_racks = qs_racks.filter(rack__tienda_id=tienda_id)
        qs_plantas = qs_plantas.filter(planta__tienda_id=tienda_id)
    
    if fecha_inicio:
        qs_racks = qs_racks.filter(hora_inicio__date__gte=fecha_inicio)
        qs_plantas = qs_plantas.filter(hora_inicio__date__gte=fecha_inicio)
    if fecha_fin:
        qs_racks = qs_racks.filter(hora_inicio__date__lte=fecha_fin)
        qs_plantas = qs_plantas.filter(hora_inicio__date__lte=fecha_fin)

    # Marcamos el tipo para el template
    for r in qs_racks: r.tipo_equipo = 'Rack'
    for p in qs_plantas: p.tipo_equipo = 'Planta'

    merged = sorted(
        chain(qs_racks, qs_plantas),
        key=lambda x: x.hora_inicio,
        reverse=True
    )
    return merged


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

        # Conteos
        conteo_racks = racks_qs.count()
        conteo_plantas = plantas_qs.count()
        context['visitas_conteo'] = conteo_racks + conteo_plantas
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

        # Contexto para selectores
        tiendas = list(Tienda.objects.all().order_by('nombre'))
        for t in tiendas: t.pk_str = str(t.pk)
        context['tiendas'] = tiendas
        
        context['tienda_seleccionada'] = tienda_id
        context['fecha_inicio_seleccionada'] = fecha_inicio_str
        context['fecha_fin_seleccionada'] = fecha_fin_str
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
            es_rack = hasattr(r, 'rack')
            equipo = r.rack.id_qr if es_rack else r.planta.id_qr
            tienda = r.rack.tienda.nombre if es_rack else r.planta.tienda.nombre
            tipo_act = r.get_tipo_actividad_display() if es_rack else 'Revisión Mensual'
            
            writer.writerow([
                r.hora_inicio.strftime('%d/%m/%Y %H:%M') if r.hora_inicio else '',
                tecnico,
                equipo,
                tienda,
                r.tipo_equipo,
                tipo_act,
                'Cerrado' if r.cerrado else 'Abierto',
                r.duracion_minutos() if r.hora_fin else '—',
            ])
            
        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="reporte_unificado_sgmr.csv"'
        return response
