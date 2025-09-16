# productos/models.py

from django.db import models
from django.contrib.auth.models import AbstractUser
from decimal import Decimal
from django.core.exceptions import ValidationError
import os

class Rol(models.Model):
    nombre = models.CharField('Nombre del rol', max_length=50)

    def __str__(self):
        return self.nombre
    
# Crear rol por defecto
def get_default_rol():
    """Retorna el rol 'usuario' por defecto"""
    rol, created = Rol.objects.get_or_create(
        nombre='usuario', 
        defaults={'nombre': 'usuario'}
    )
    return rol.id

class Usuario(AbstractUser):
    rol = models.ForeignKey(
        Rol, on_delete=models.SET_NULL,
        null=True, verbose_name='Rol',
        default=get_default_rol
    )
    dui = models.CharField('DUI', max_length=9, unique=True)
    SEXO_CHOICES = [('M','Masculino'), ('F','Femenino')]
    sexo = models.CharField('Sexo', max_length=1, choices=SEXO_CHOICES)
    edad = models.PositiveIntegerField('Edad', null=True, blank=True)
    telefono = models.CharField('Teléfono', max_length=20, blank=True)
    activo = models.BooleanField('Usuario Activo', default=False, 
                               help_text='Solo usuarios activos pueden acceder al sistema')
    
    # NUEVO CAMPO PARA SUCURSAL
    sucursal = models.ForeignKey(
        'dte.Sucursal', 
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Sucursal Asignada',
        help_text='Sucursal a la que pertenece el usuario'
    )

    REQUIRED_FIELDS = ['email', 'first_name', 'last_name', 'dui']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.username})"
    
    def puede_acceder(self):
        """Verifica si el usuario puede acceder al sistema"""
        return (
            self.is_authenticated and
            self.is_active and
            self.activo and
            self.rol and
            self.rol.nombre == 'administrador'
        )


class Categoria(models.Model):
    nombre      = models.CharField('Nombre', max_length=100)
    descripcion = models.TextField('Descripción', blank=True)

    def __str__(self):
        return self.nombre

class Proveedor(models.Model):
    nombre    = models.CharField('Nombre', max_length=100)
    nrc       = models.CharField('NRC', max_length=20)
    contacto  = models.CharField('Contacto', max_length=100)
    email     = models.EmailField('Correo', blank=True)
    telefono  = models.CharField('Teléfono', max_length=20, blank=True)
    direccion = models.TextField('Dirección', blank=True)

    def __str__(self):
        return f"{self.nombre} ({self.nrc})"

# Validadores para imágenes
def validate_image_size(image):
    """Validar que la imagen no sea mayor a 5MB"""
    if image.size > 5 * 1024 * 1024:
        raise ValidationError('La imagen no puede ser mayor a 5MB.')

def validate_image_format(image):
    """Validar formato de imagen"""
    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    ext = os.path.splitext(image.name)[1].lower()
    if ext not in valid_extensions:
        raise ValidationError('Formato no válido. Use JPG, PNG, GIF o WebP.')

# CORREGIDO: Función de path personalizada
def producto_image_path(instance, filename):
    """Función personalizada para el path de las imágenes"""
    # Sanitizar el nombre del archivo
    name, ext = os.path.splitext(filename)
    safe_filename = f"{name}_{instance.codigo1}{ext}" if instance.codigo1 else filename
    
    # Retornar el path: productos/codigo_producto/filename
    if instance.codigo1:
        return f'productos/{instance.codigo1}/{safe_filename}'
    else:
        return f'productos/temp/{safe_filename}'

class Producto(models.Model):
    nombre = models.CharField("Nombre", max_length=100)
    descripcion = models.TextField("Descripción", blank=True)
    
    # Códigos y precios
    codigo1 = models.CharField("Código 1", max_length=25, unique=True)
    codigo2 = models.CharField("Código 2", max_length=25, blank=True, null=True)
    codigo3 = models.CharField("Código 3", max_length=25, blank=True, null=True)
    codigo4 = models.CharField("Código 4", max_length=25, blank=True, null=True)
    
    precio1 = models.DecimalField("Precio 1", max_digits=10, decimal_places=2)
    precio2 = models.DecimalField("Precio 2", max_digits=10, decimal_places=2, blank=True, null=True)
    precio3 = models.DecimalField("Precio 3", max_digits=10, decimal_places=2, blank=True, null=True)
    precio4 = models.DecimalField("Precio 4", max_digits=10, decimal_places=2, blank=True, null=True)
    
    # CORREGIDO: Imágenes usando la función personalizada
    imagen1 = models.ImageField(
        "Imagen 1", 
        upload_to=producto_image_path,  # Usar la función personalizada
        null=True, 
        blank=True,
        validators=[validate_image_size, validate_image_format]
    )
    imagen2 = models.ImageField(
        "Imagen 2", 
        upload_to=producto_image_path, 
        null=True, 
        blank=True,
        validators=[validate_image_size, validate_image_format]
    )
    imagen3 = models.ImageField(
        "Imagen 3", 
        upload_to=producto_image_path, 
        null=True, 
        blank=True,
        validators=[validate_image_size, validate_image_format]
    )
    imagen4 = models.ImageField(
        "Imagen 4", 
        upload_to=producto_image_path, 
        null=True, 
        blank=True,
        validators=[validate_image_size, validate_image_format]
    )
    
    # Resto de campos...
    DESCUENTOS = [(i, f"{i}%") for i in range(0, 55, 5)]
    descuento_por_defecto = models.PositiveSmallIntegerField(
        "Descuento %", choices=DESCUENTOS, default=0
    )
    
    existencias = models.PositiveIntegerField("Existencias", default=0)
    categoria = models.ForeignKey(
        "Categoria", on_delete=models.SET_NULL,
        null=True, related_name="productos",
        verbose_name="Categoría"
    )
    proveedor = models.ForeignKey(
        "Proveedor", on_delete=models.SET_NULL,
        null=True, related_name="productos",
        verbose_name="Proveedor"
    )

    def precio_por_indice(self, indice):
        """
        Devuelve el precio según el índice:
        1 = precio1, 2 = precio2, 3 = precio3, 4 = precio4
        """
        if indice == 1:
            return self.precio1
        elif indice == 2:
            return self.precio2 if self.precio2 is not None else self.precio1
        elif indice == 3:
            return self.precio3 if self.precio3 is not None else self.precio1
        elif indice == 4:
            return self.precio4 if self.precio4 is not None else self.precio1
        else:
            return self.precio1  # Por defecto

    def get_precios_disponibles(self):
        """
        Devuelve una lista de tuplas (índice, precio) para los precios disponibles
        """
        precios = []
        
        if self.precio1 is not None:
            precios.append((1, f"Precio 1: ${self.precio1:.2f}"))
        
        if self.precio2 is not None:
            precios.append((2, f"Precio 2: ${self.precio2:.2f}"))
        
        if self.precio3 is not None:
            precios.append((3, f"Precio 3: ${self.precio3:.2f}"))
        
        if self.precio4 is not None:
            precios.append((4, f"Precio 4: ${self.precio4:.2f}"))
        
        return precios
    
    def __str__(self):
        return self.nombre

class Tercero(models.Model):
    nombres   = models.CharField('Nombres', max_length=100)
    apellidos = models.CharField('Apellidos', max_length=100)
    telefono  = models.CharField('Teléfono', max_length=20)
    correo    = models.EmailField('Correo')
    dui       = models.CharField('DUI', max_length=9, unique=True)
    edad      = models.PositiveIntegerField('Edad')
    SEXO_CHOICES = [('M','Masculino'),('F','Femenino')]
    sexo      = models.CharField('Sexo', max_length=1, choices=SEXO_CHOICES)
    direccion = models.TextField('Dirección')

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"

class Reserva(models.Model):
    tercero = models.ForeignKey(
        Tercero, on_delete=models.CASCADE,
        related_name='reservas', verbose_name='Tercero'
    )
    fecha   = models.DateTimeField('Fecha de reserva', auto_now_add=True)

    def __str__(self):
        return f"Reserva #{self.id} - {self.tercero}"

class ItemReserva(models.Model):
    reserva  = models.ForeignKey(
        Reserva, on_delete=models.CASCADE,
        related_name='items', verbose_name='Reserva'
    )
    producto = models.ForeignKey(
        Producto, on_delete=models.CASCADE, verbose_name='Producto'
    )
    cantidad = models.PositiveIntegerField('Cantidad')

    def __str__(self):
        return f"{self.cantidad} × {self.producto}"

# Señales para manejo de archivos
from django.db.models.signals import pre_save, post_delete, pre_delete
from django.dispatch import receiver
from django.conf import settings

@receiver(pre_save, sender=Producto)
def producto_pre_save(sender, instance, **kwargs):
    """
    Elimina imágenes antiguas cuando se actualiza un producto
    """
    if not instance.pk:
        return  # Es un objeto nuevo, no hacer nada
    
    try:
        old_instance = Producto.objects.get(pk=instance.pk)
    except Producto.DoesNotExist:
        return
    
    # Verificar cada campo de imagen
    for i in range(1, 5):
        old_image = getattr(old_instance, f'imagen{i}')
        new_image = getattr(instance, f'imagen{i}')
        
        # Si había una imagen anterior y ahora es diferente (o None), eliminarla
        if old_image and old_image != new_image:
            image_path = os.path.join(settings.MEDIA_ROOT, old_image.name)
            if os.path.exists(image_path):
                try:
                    os.remove(image_path)
                    print(f"Imagen eliminada: {image_path}")
                except OSError as e:
                    print(f"Error al eliminar imagen: {e}")

@receiver(post_delete, sender=Producto)
def producto_post_delete(sender, instance, **kwargs):
    """
    Elimina todas las imágenes cuando se elimina un producto
    """
    for i in range(1, 5):
        image = getattr(instance, f'imagen{i}')
        if image:
            image_path = os.path.join(settings.MEDIA_ROOT, image.name)
            if os.path.exists(image_path):
                try:
                    os.remove(image_path)
                    print(f"Imagen eliminada al borrar producto: {image_path}")
                except OSError as e:
                    print(f"Error al eliminar imagen: {e}")