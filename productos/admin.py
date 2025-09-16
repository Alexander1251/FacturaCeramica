from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    Categoria, Proveedor, Producto,
    Tercero, Reserva, ItemReserva, Rol, Usuario
)

admin.site.register(Categoria)
admin.site.register(Proveedor)
admin.site.register(Producto)
admin.site.register(Tercero)

class ItemReservaInline(admin.TabularInline):
    model = ItemReserva
    extra = 1

@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ('id','tercero','fecha')
    inlines     = [ItemReservaInline]

@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ('nombre',)

@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    model = Usuario
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('rol','dui','sexo','edad','telefono')}),
    )
    list_display = ('username','email','first_name','last_name','rol')
