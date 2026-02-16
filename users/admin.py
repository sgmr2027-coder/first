from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Tecnico


@admin.register(Tecnico)
class TecnicoAdmin(BaseUserAdmin):
    list_display = ('username', 'nombre_completo', 'rol', 'activo', 'is_staff')
    list_filter = ('rol', 'activo')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('SGMR', {'fields': ('rol', 'activo', 'nombre_completo')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('SGMR', {'fields': ('rol', 'activo', 'nombre_completo')}),
    )
