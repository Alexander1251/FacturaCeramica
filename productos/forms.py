# productos/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError
import os

from .models import (
    Usuario, Rol,
    Categoria, Proveedor, Producto,
    Tercero, Reserva, ItemReserva
)

# ─────────────────────────────────────────────────────────────────────────────
# Mixin para inyectar clases Bootstrap a todos los campos
# ─────────────────────────────────────────────────────────────────────────────
class BootstrapFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            css = 'form-select' if isinstance(f.widget, forms.Select) else 'form-control'
            f.widget.attrs.update({'class': css})

class LoginForm(BootstrapFormMixin, AuthenticationForm):
    """ AuthenticationForm + inyección de form-control """
    pass

class RegistroForm(BootstrapFormMixin, UserCreationForm):
    """ UserCreationForm + inyección de form-control """
    email = forms.EmailField()
    rol   = forms.ModelChoiceField(queryset=Rol.objects.all())
    class Meta:
        model  = Usuario
        fields = [
          'username','email','first_name','last_name',
          'dui','edad','sexo','telefono','rol',
          'password1','password2'
        ]

# ─────────────────────────────────────────────────────────────────────────────
# ModelForms para CRUD
# ─────────────────────────────────────────────────────────────────────────────
class CategoriaForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Categoria
        fields = '__all__'

class ProveedorForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = '__all__'

# CORREGIDO: Formulario de Producto con debug mejorado
class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [
            'nombre', 'descripcion', 'codigo1', 'codigo2', 'codigo3', 'codigo4',
            'precio1', 'precio2', 'precio3', 'precio4', 'descuento_por_defecto',
            'existencias', 'categoria', 'proveedor', 'imagen1', 'imagen2', 'imagen3', 'imagen4'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del producto'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descripción del producto'}),
            'codigo1': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código principal'}),
            'codigo2': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código alternativo (opcional)'}),
            'codigo3': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código alternativo (opcional)'}),
            'codigo4': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código alternativo (opcional)'}),
            'precio1': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'precio2': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'precio3': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'precio4': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'descuento_por_defecto': forms.Select(attrs={'class': 'form-select'}),
            'existencias': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'proveedor': forms.Select(attrs={'class': 'form-select'}),
            'imagen1': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'imagen2': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'imagen3': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'imagen4': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print("=== DEBUG: Inicializando ProductoForm ===")
        print(f"args: {args}")
        print(f"kwargs: {kwargs}")
        
        # Debug: verificar si tenemos archivos
        if len(args) > 1:  # POST data y FILES
            print(f"FILES en args[1]: {args[1] if len(args) > 1 else 'No FILES'}")

    def clean(self):
        cleaned_data = super().clean()
        print("=== DEBUG: clean() method ===")
        print(f"cleaned_data keys: {list(cleaned_data.keys())}")
        
        # Debug: verificar imágenes en cleaned_data
        for i in range(1, 5):
            imagen_key = f'imagen{i}'
            if imagen_key in cleaned_data:
                imagen = cleaned_data[imagen_key]
                print(f"{imagen_key}: {imagen} (type: {type(imagen)})")
                if imagen:
                    print(f"  - name: {imagen.name}")
                    print(f"  - size: {imagen.size}")
        
        return cleaned_data

    def clean_imagen1(self):
        imagen = self.cleaned_data.get('imagen1')
        print(f"=== DEBUG: clean_imagen1 ===")
        print(f"imagen1: {imagen} (type: {type(imagen)})")
        return self.validate_image(imagen, 'imagen1')
    
    def clean_imagen2(self):
        imagen = self.cleaned_data.get('imagen2')
        print(f"=== DEBUG: clean_imagen2 ===")
        print(f"imagen2: {imagen} (type: {type(imagen)})")
        return self.validate_image(imagen, 'imagen2')
    
    def clean_imagen3(self):
        imagen = self.cleaned_data.get('imagen3')
        print(f"=== DEBUG: clean_imagen3 ===")
        print(f"imagen3: {imagen} (type: {type(imagen)})")
        return self.validate_image(imagen, 'imagen3')
    
    def clean_imagen4(self):
        imagen = self.cleaned_data.get('imagen4')
        print(f"=== DEBUG: clean_imagen4 ===")
        print(f"imagen4: {imagen} (type: {type(imagen)})")
        return self.validate_image(imagen, 'imagen4')

    def validate_image(self, image, field_name):
        print(f"=== DEBUG: validate_image para {field_name} ===")
        print(f"image: {image}")
        
        if image:
            print(f"Validando imagen: {image.name}")
            print(f"Tamaño: {image.size} bytes")
            
            # Validar tamaño del archivo (máximo 5MB)
            if image.size > 5 * 1024 * 1024:
                raise ValidationError('El archivo de imagen no puede ser mayor a 5MB.')
            
            # Validar extensión del archivo
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
            ext = os.path.splitext(image.name)[1].lower()
            print(f"Extensión detectada: {ext}")
            
            if ext not in valid_extensions:
                raise ValidationError('Formato de imagen no válido. Use JPG, PNG, GIF o WebP.')
                
            print(f"Imagen {field_name} validada correctamente")
        else:
            print(f"No hay imagen para {field_name}")
        
        return image

class TerceroForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Tercero
        fields = '__all__'

# ─────────────────────────────────────────────────────────────────────────────
# ItemReserva como ModelForm + formset
# ─────────────────────────────────────────────────────────────────────────────
class ItemReservaForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ItemReserva
        fields = ['producto', 'cantidad']

ItemReservaFormSet = inlineformset_factory(
    Reserva, ItemReserva,
    form=ItemReservaForm,
    extra=1, can_delete=False
)

class UsuarioGestionForm(forms.ModelForm):
    """Formulario para que administradores gestionen usuarios"""
    
    class Meta:
        model = Usuario
        fields = ['username', 'first_name', 'last_name', 'email', 'rol', 'activo', 'is_active', 'sucursal']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'readonly': True}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'rol': forms.Select(attrs={'class': 'form-select'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sucursal': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'username': 'Nombre de Usuario',
            'first_name': 'Nombres',
            'last_name': 'Apellidos',
            'email': 'Correo Electrónico',
            'rol': 'Rol del Usuario',
            'activo': 'Usuario Activo (puede acceder)',
            'is_active': 'Cuenta Activa (Django)',
            'sucursal': 'Sucursal Asignada',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Mostrar solo sucursales activas
        from dte.models import Sucursal
        self.fields['sucursal'].queryset = Sucursal.objects.filter(activa=True).order_by('nombre')
        self.fields['sucursal'].required = False
        self.fields['sucursal'].empty_label = "Sin sucursal asignada"
        
        # Ayuda contextual
        self.fields['sucursal'].help_text = "Sucursal a la que pertenece el usuario para facturación"