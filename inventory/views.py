from django.shortcuts import get_object_or_404
from django.http import JsonResponse

from .models import Rack


def rack_by_qr(request, id_qr):
    """API: Buscar rack por ID del QR. Usado por el escáner."""
    rack = get_object_or_404(Rack, id_qr=id_qr, activo=True)
    return JsonResponse({
        'id': rack.pk,
        'id_qr': rack.id_qr,
        'tienda': rack.tienda.nombre,
        'marca': rack.marca,
        'modelo': rack.modelo,
        'ubicacion': rack.ubicacion,
        'compresores_media': rack.compresores_media,
        'compresores_baja': rack.compresores_baja,
        'total_compresores': rack.total_compresores,
    })
