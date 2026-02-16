from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.db.models import Avg, F, ExpressionWrapper, DurationField
from operations.models import RegistroActividad


class DashboardView(LoginRequiredMixin, TemplateView):
    """Vista básica para reportes comparativos y MTTR."""
    template_name = 'analytics/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cerrados = RegistroActividad.objects.filter(cerrado=True, hora_fin__isnull=False)
        context['total_intervenciones'] = cerrados.count()
        if cerrados.exists():
            duracion_expr = ExpressionWrapper(
                F('hora_fin') - F('hora_inicio'),
                output_field=DurationField()
            )
            agg = cerrados.annotate(duracion=duracion_expr).aggregate(promedio=Avg('duracion'))
            promedio_td = agg.get('promedio')
            if promedio_td:
                context['mttr_minutos'] = round(promedio_td.total_seconds() / 60, 1)
            else:
                context['mttr_minutos'] = None
        else:
            context['mttr_minutos'] = None
        return context
