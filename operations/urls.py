from django.urls import path
from . import views
 
app_name = 'operations'
 
urlpatterns = [
    # ── Scanner unificado ─────────────────────────────────────────────────────
    path('scanner/', views.ScannerView.as_view(), name='scanner'),
 
    # ── Rack — flujo completo ─────────────────────────────────────────────────
    path('rack/<int:rack_id>/',              views.FichaTecnicaView.as_view(),   name='ficha'),
    path('rack/<int:rack_id>/iniciar/',      views.IniciarActividadView.as_view(),name='iniciar'),
    path('registro/<int:registro_id>/checkin/',        views.CheckInView.as_view(),      name='checkin'),
    path('registro/<int:registro_id>/checkin/saltar/', views.SaltarCheckInView.as_view(),name='saltar_checkin'),
    path('registro/<int:registro_id>/checkout/',       views.CheckOutView.as_view(),     name='checkout'),
    path('registro/<int:registro_id>/pdf/',            views.IntervencionPDFView.as_view(), name='pdf_rack'),
 
    # ── Rack — API QR ─────────────────────────────────────────────────────────
    path('api/rack/<str:id_qr>/', views.api_rack_qr, name='api_rack_qr'),
 
    # ── Planta Eléctrica — flujo completo ────────────────────────────────────
    path('planta/<int:planta_id>/',          views.FichaPlantaView.as_view(),          name='ficha_planta'),
    path('planta/<int:planta_id>/iniciar/',  views.IniciarRevisionPlantaView.as_view(),name='iniciar_planta'),
    path('planta/revision/<int:registro_id>/', views.RevisionPlantaView.as_view(),     name='revision_planta'),
    path('planta/revision/<int:registro_id>/pdf/', views.PlantaPDFView.as_view(),      name='pdf_planta'),
 
    # ── Planta Eléctrica — API QR ────────────────────────────────────────────
    path('api/planta/<str:id_qr>/', views.api_planta_qr, name='api_planta_qr'),
]