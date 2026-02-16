from django.urls import path
from . import views

app_name = 'inventory'
urlpatterns = [
    path('api/rack/<str:id_qr>/', views.rack_by_qr, name='rack_by_qr'),
]
