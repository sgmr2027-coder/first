"""
URL configuration for SGMR.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('users.urls')),
    path('', include('inventory.urls')),
    path('', include('operations.urls')),
    path('', include('analytics.urls')),
]
