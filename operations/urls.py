from django.urls import path
from . import views

app_name = 'operations'
urlpatterns = [
    path('scanner/', views.ScannerView.as_view(), name='scanner'),
    path('rack/<int:rack_id>/', views.FichaTecnicaView.as_view(), name='ficha'),
    path('rack/<int:rack_id>/iniciar/', views.IniciarActividadView.as_view(), name='iniciar'),
    path('registro/<int:registro_id>/entrada/', views.CheckInView.as_view(), name='checkin'),
    path('registro/<int:registro_id>/salida/', views.CheckOutView.as_view(), name='checkout'),
    path('api/rack-qr/<str:id_qr>/', views.api_rack_qr, name='api_rack_qr'),
]
