from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login as auth_login
from django.contrib.auth.views import LoginView, LogoutView
from django.http import JsonResponse
from django.db.models import Q
from django.urls import reverse

from .models import (
    Categoria, Proveedor, Producto,
    Tercero, Reserva, ItemReserva, Rol, Usuario
)
from .forms import (
    CategoriaForm, ProveedorForm,
    ProductoForm, TerceroForm,
    ItemReservaFormSet, RegistroForm, LoginForm, UsuarioGestionForm
)

# — Login/Logout/Registro —
class CustomLoginView(LoginView):
    template_name = 'registration/login.html'
    authentication_form = LoginForm
    
    def form_valid(self, form):
        """Override para verificar permisos después del login"""
        # Primero hacer el login normal
        response = super().form_valid(form)
        
        # Verificar si el usuario puede acceder al sistema
        if not self.request.user.puede_acceder():
            # Si no puede acceder, no hacer logout automático
            # Solo redirigir a la página de acceso denegado
            messages.warning(
                self.request,
                'Ha iniciado sesión correctamente, pero su cuenta no tiene permisos '
                'para acceder al sistema. Contacte al administrador.'
            )
            return redirect('acceso_denegado')
        
        # Si puede acceder, continuar normalmente
        messages.success(self.request, f'Bienvenido, {self.request.user.first_name}!')
        return response
    
    def form_invalid(self, form):
        """Mejorar mensajes de error de login"""
        messages.error(
            self.request,
            'Credenciales incorrectas. Verifique su usuario y contraseña.'
        )
        return super().form_invalid(form)

class CustomLogoutView(LogoutView):
    next_page = 'login'   # redirige al login tras cerrar sesión

def registro(request):
    # Si el usuario ya está logueado y puede acceder, redirigir al home
    if request.user.is_authenticated and request.user.puede_acceder():
        return redirect('home')
    
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            # Asegurar que el usuario tenga rol 'usuario' y esté inactivo
            rol_usuario, created = Rol.objects.get_or_create(nombre='usuario')
            user.rol = rol_usuario
            user.activo = False  # Inactivo hasta que admin lo active
            user.is_active = True  # Cuenta activa en Django (para poder hacer login)
            user.save()
            
            messages.success(request, 
                'Cuenta creada exitosamente. Su cuenta está pendiente de activación por un administrador. '
                'Puede iniciar sesión, pero no podrá acceder al sistema hasta ser activado.')
            return redirect('login')
        else:
            messages.error(request, 'Por favor corrija los errores en el formulario.')
    else:
        form = RegistroForm()
    return render(request, 'registration/register.html', {'form': form})

class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'productos/home.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Si el usuario no puede acceder, redirigir a acceso denegado
        if not request.user.puede_acceder():
            return redirect('acceso_denegado')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Agregar estadísticas básicas para administradores
        context.update({
            'total_usuarios': Usuario.objects.count(),
            'usuarios_activos': Usuario.objects.filter(activo=True).count(),
            'usuarios_pendientes': Usuario.objects.filter(activo=False).count(),
            'total_productos': Producto.objects.count(),
        })
        return context

# — Mixin para restringir solo a rol "administrador" —
class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        # ACTUALIZADO: Usar el nuevo método puede_acceder
        return (
            self.request.user.is_authenticated and
            self.request.user.puede_acceder()
        )

    def handle_no_permission(self):
        return super().handle_no_permission()


# —— CRUD Categorías —— 
class CategoriaListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = Categoria
    template_name = 'productos/catalogos/categoria/list.html'

class CategoriaCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = Categoria
    form_class = CategoriaForm
    template_name = 'productos/catalogos/categoria/form.html'
    success_url = reverse_lazy('categoria_list')

class CategoriaUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = Categoria
    form_class = CategoriaForm
    template_name = 'productos/catalogos/categoria/form.html'
    success_url = reverse_lazy('categoria_list')

class CategoriaDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    model = Categoria
    template_name = 'productos/catalogos/categoria/confirm_delete.html'
    success_url = reverse_lazy('categoria_list')


# —— CRUD Proveedores —— 
class ProveedorListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = Proveedor
    template_name = 'productos/catalogos/proveedor/list.html'

class ProveedorCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = Proveedor
    form_class = ProveedorForm
    template_name = 'productos/catalogos/proveedor/form.html'
    success_url = reverse_lazy('proveedor_list')

class ProveedorUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = Proveedor
    form_class = ProveedorForm
    template_name = 'productos/catalogos/proveedor/form.html'
    success_url = reverse_lazy('proveedor_list')

class ProveedorDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    model = Proveedor
    template_name = 'productos/catalogos/proveedor/confirm_delete.html'
    success_url = reverse_lazy('proveedor_list')


# —— CRUD Productos —— 
from django.http import JsonResponse
from django.db.models import Q

class ProductoListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = Producto
    template_name = 'productos/catalogos/producto/list.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object_list'] = []  # Empty list for server-side processing
        return context

def producto_datatable_view(request):
    # Get DataTables parameters
    draw = int(request.GET.get('draw', 1))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]', '')
    order_column = int(request.GET.get('order[0][column]', 1))
    order_dir = request.GET.get('order[0][dir]', 'asc')
    
    # Map column index to model field
    column_map = {
        0: 'id',
        1: 'nombre',
        2: 'codigo1',
        3: 'precio1',
        4: 'descuento_por_defecto',
        5: 'categoria__nombre',
        6: 'proveedor__nombre',
        7: 'existencias',
    }
    
    # Get ordering field
    order_field = column_map.get(order_column, 'nombre')
    if order_dir == 'desc':
        order_field = f'-{order_field}'
    
    # Build queryset
    queryset = Producto.objects.select_related('categoria', 'proveedor')
    
    # Apply search filter
    if search_value:
        queryset = queryset.filter(
            Q(nombre__icontains=search_value) |
            Q(codigo1__icontains=search_value) |
            Q(categoria__nombre__icontains=search_value) |
            Q(proveedor__nombre__icontains=search_value)
        )
    
    # Get total records count
    total_records = queryset.count()
    
    # Apply ordering and pagination
    queryset = queryset.order_by(order_field)[start:start + length]
    
    # Prepare data for response
    data = []
    for idx, producto in enumerate(queryset, start=start+1):
        # Badge para existencias
        if producto.existencias <= 5:
            existencias = f'<span class="badge bg-danger">{producto.existencias}</span>'
        elif producto.existencias <= 10:
            existencias = f'<span class="badge bg-warning text-dark">{producto.existencias}</span>'
        else:
            existencias = f'<span class="badge bg-success">{producto.existencias}</span>'
        
        # Imagen preview - CORREGIDO
        imagen_html = ''
        if producto.imagen1:
            try:
                imagen_html = f'''
                    <img src="{producto.imagen1.url}" 
                         alt="Imagen {producto.nombre}" 
                         class="img-thumbnail product-thumb" 
                         style="width: 50px; height: 50px; object-fit: cover; cursor: pointer;"
                         onclick="showImageModal('{producto.imagen1.url}', '{producto.nombre}')"
                         onerror="this.onerror=null; this.style.display='none'; this.parentElement.innerHTML='<span class=\\'text-danger\\'>Error</span>';">
                '''
            except Exception as e:
                imagen_html = '<span class="text-muted"><i class="fas fa-image"></i> Error</span>'
        else:
            imagen_html = '<span class="text-muted"><i class="fas fa-image"></i> Sin imagen</span>'
        
        # Action buttons
        actions = f'''
            <div class="btn-group" role="group">
                <a href="{reverse('producto_detail', args=[producto.id])}" 
                   class="btn btn-sm btn-info" title="Ver">
                    <i class="fas fa-eye"></i>
                </a>
                <a href="{reverse('producto_update', args=[producto.id])}" 
                   class="btn btn-sm btn-warning" title="Editar">
                    <i class="fas fa-edit"></i>
                </a>
                <a href="{reverse('producto_delete', args=[producto.id])}" 
                   class="btn btn-sm btn-danger" title="Eliminar">
                    <i class="fas fa-trash"></i>
                </a>
            </div>
        '''
        
        data.append([
            idx,
            producto.nombre,
            producto.codigo1,
            f"${producto.precio1:.2f}",
            producto.get_descuento_por_defecto_display(),
            producto.categoria.nombre if producto.categoria else '',
            producto.proveedor.nombre if producto.proveedor else '',
            existencias,
            imagen_html,
            actions
        ])
    
    # Prepare response
    response = {
        'draw': draw,
        'recordsTotal': Producto.objects.count(),
        'recordsFiltered': total_records,
        'data': data
    }
    
    return JsonResponse(response)

# ===== 8. VISTA ACTUALIZADA (productos/views.py) =====
from django.views.generic import CreateView, UpdateView
from django.contrib import messages
from django.urls import reverse_lazy

class ProductoCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = Producto
    form_class = ProductoForm
    template_name = 'productos/catalogos/producto/form.html'
    success_url = reverse_lazy('producto_list')
    
    def post(self, request, *args, **kwargs):
        """Override post para debug detallado"""
        print("=== DEBUG: ProductoCreateView.post ===")
        print(f"request.method: {request.method}")
        print(f"request.POST keys: {list(request.POST.keys())}")
        print(f"request.FILES keys: {list(request.FILES.keys())}")
        
        # Debug archivos específicos
        for i in range(1, 5):
            file_key = f'imagen{i}'
            if file_key in request.FILES:
                file_obj = request.FILES[file_key]
                print(f"{file_key}: {file_obj.name} ({file_obj.size} bytes)")
            else:
                print(f"{file_key}: No presente en request.FILES")
        
        return super().post(request, *args, **kwargs)
    
    def form_valid(self, form):
        """Debug cuando el formulario es válido"""
        print("=== DEBUG: ProductoCreateView.form_valid ===")
        
        # Guardar el objeto
        response = super().form_valid(form)
        producto = self.object
        
        print(f"Producto creado con ID: {producto.id}")
        print(f"Código del producto: {producto.codigo1}")
        
        # Debug: verificar que las imágenes se guardaron
        for i in range(1, 5):
            imagen = getattr(producto, f'imagen{i}')
            if imagen:
                print(f"Imagen {i}:")
                print(f"  - Nombre en BD: {imagen.name}")
                print(f"  - URL: {imagen.url}")
                if hasattr(imagen, 'path'):
                    print(f"  - Path completo: {imagen.path}")
                    print(f"  - Archivo existe: {os.path.exists(imagen.path)}")
                else:
                    print(f"  - No tiene atributo 'path'")
            else:
                print(f"Imagen {i}: No definida")
        
        messages.success(self.request, 'Producto creado correctamente.')
        return response
    
    def form_invalid(self, form):
        """Debug cuando el formulario tiene errores"""
        print("=== DEBUG: ProductoCreateView.form_invalid ===")
        print("Errores en el formulario:")
        for field, errors in form.errors.items():
            print(f"  {field}: {errors}")
        
        # Debug: verificar si hay errores en archivos
        for i in range(1, 5):
            field_name = f'imagen{i}'
            if field_name in form.errors:
                print(f"Error en {field_name}: {form.errors[field_name]}")
        
        messages.error(self.request, 'Por favor corrija los errores en el formulario.')
        return super().form_invalid(form)

import os
from django.conf import settings
from django.contrib import messages

class ProductoUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = Producto
    form_class = ProductoForm
    template_name = 'productos/catalogos/producto/form.html'
    success_url = reverse_lazy('producto_list')
    
    def post(self, request, *args, **kwargs):
        """Override post para manejar eliminación de imágenes y debug"""
        print("=== DEBUG: ProductoUpdateView.post ===")
        print(f"request.POST keys: {list(request.POST.keys())}")
        print(f"request.FILES keys: {list(request.FILES.keys())}")
        
        self.object = self.get_object()
        
        # Manejar eliminación de imágenes ANTES de procesar el formulario
        for i in range(1, 5):
            delete_field = f'delete_imagen{i}'
            imagen_field = f'imagen{i}'
            
            if request.POST.get(delete_field) == 'true':
                print(f"Eliminando {imagen_field}")
                current_image = getattr(self.object, imagen_field)
                
                if current_image:
                    # Eliminar el archivo físico
                    image_path = os.path.join(settings.MEDIA_ROOT, current_image.name)
                    print(f"Intentando eliminar: {image_path}")
                    
                    if os.path.exists(image_path):
                        try:
                            os.remove(image_path)
                            print(f"Archivo eliminado: {image_path}")
                        except OSError as e:
                            print(f"Error al eliminar archivo: {e}")
                            messages.warning(request, f'No se pudo eliminar la imagen física: {e}')
                    
                    # Limpiar el campo en el modelo
                    setattr(self.object, imagen_field, None)
                    print(f"Campo {imagen_field} limpiado en el modelo")
        
        # Guardar cambios de eliminación
        self.object.save()
        print("Cambios de eliminación guardados")
        
        # Continuar con el procesamiento normal del formulario
        return super().post(request, *args, **kwargs)
    
    def form_valid(self, form):
        print("=== DEBUG: ProductoUpdateView.form_valid ===")
        
        response = super().form_valid(form)
        producto = self.object
        
        print(f"Producto actualizado: {producto.id}")
        
        # Debug: verificar imágenes después de actualizar
        for i in range(1, 5):
            imagen = getattr(producto, f'imagen{i}')
            if imagen:
                print(f"Imagen {i} después de actualizar:")
                print(f"  - Nombre: {imagen.name}")
                print(f"  - URL: {imagen.url}")
                if hasattr(imagen, 'path'):
                    print(f"  - Existe: {os.path.exists(imagen.path)}")
        
        messages.success(self.request, 'Producto actualizado correctamente.')
        return response
    
    def form_invalid(self, form):
        print("=== DEBUG: ProductoUpdateView.form_invalid ===")
        print("Errores:", form.errors)
        messages.error(self.request, 'Por favor corrija los errores en el formulario.')
        return super().form_invalid(form)

class ProductoDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    model = Producto
    template_name = 'productos/catalogos/producto/confirm_delete.html'
    success_url = reverse_lazy('producto_list')

from django.views.generic import DetailView

class ProductoDetailView(LoginRequiredMixin, AdminRequiredMixin, DetailView):
    model = Producto
    template_name = 'productos/catalogos/producto/detail.html'
    context_object_name = 'producto'


# —— CRUD Terceros —— 
class TerceroListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = Tercero
    template_name = 'productos/catalogos/tercero/list.html'

class TerceroCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = Tercero
    form_class = TerceroForm
    template_name = 'productos/catalogos/tercero/form.html'
    success_url = reverse_lazy('tercero_list')

class TerceroUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = Tercero
    form_class = TerceroForm
    template_name = 'productos/catalogos/tercero/form.html'
    success_url = reverse_lazy('tercero_list')

class TerceroDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    model = Tercero
    template_name = 'productos/catalogos/tercero/confirm_delete.html'
    success_url = reverse_lazy('tercero_list')


# —— Vistas de Reserva (funcionales) —— 
@login_required
def lista_reservas(request):
    reservas = Reserva.objects.select_related('tercero').all()
    return render(request, 'productos/reservas/list.html', {'reservas': reservas})

@login_required
def crear_reserva(request):
    if request.method == 'POST':
        tipo = request.POST.get('tipo_tercero')
        # 1️⃣ Tercero existente
        if tipo == 'existente':
            dui = request.POST.get('dui', '').strip()
            tercero = get_object_or_404(Tercero, dui=dui)
            form_tercero = TerceroForm(instance=tercero)  # para reenviarlo al template si hay error
        # 2️⃣ Nuevo tercero
        else:
            form_tercero = TerceroForm(request.POST)
            if not form_tercero.is_valid():
                formset = ItemReservaFormSet(request.POST)
                return render(request, 'productos/reservas/form.html', {
                    'form_tercero': form_tercero,
                    'formset': formset,
                    'modo': 'crear',
                })
            tercero = form_tercero.save()
        # Procesar los items de reserva
        formset = ItemReservaFormSet(request.POST)
        if formset.is_valid():
            reserva = Reserva.objects.create(tercero=tercero)
            for item in formset.save(commit=False):
                item.reserva = reserva
                prod = item.producto
                prod.existencias -= item.cantidad
                prod.save()
                item.save()
            return redirect('reserva_list')
    else:
        form_tercero = TerceroForm()
        formset     = ItemReservaFormSet()
    return render(request, 'productos/reservas/form.html', {
        'form_tercero': form_tercero,
        'formset': formset,
        'modo': 'crear',
    })

@login_required
def editar_reserva(request, pk):
    reserva = get_object_or_404(Reserva, pk=pk)
    terceros_list = Tercero.objects.all()
    if request.method == 'POST':
        tipo = request.POST.get('tipo_tercero')
        formset = ItemReservaFormSet(request.POST, instance=reserva)
        if tipo == 'existente':
            dui_existente = request.POST.get('dui_existente')
            tercero = get_object_or_404(Tercero, dui=dui_existente)
        else:
            form_ter = TerceroForm(request.POST, instance=reserva.tercero)
            if form_ter.is_valid():
                tercero = form_ter.save()
            else:
                tercero = None

        if tercero and formset.is_valid():
            # revertir stock original
            for item_old in reserva.items.all():
                prod = item_old.producto
                prod.existencias += item_old.cantidad
                prod.save()
            # borrar items viejos
            reserva.items.all().delete()

            reserva.tercero = tercero
            reserva.save()

            # guardar nuevos items
            for item in formset.save(commit=False):
                item.reserva = reserva
                prod = item.producto
                prod.existencias -= item.cantidad
                prod.save()
                item.save()
            return redirect('reserva_list')
    else:
        form_ter = TerceroForm(instance=reserva.tercero)
        formset  = ItemReservaFormSet(instance=reserva)

    return render(request, 'productos/reservas/form.html', {
        'terceros':     terceros_list,
        'form_tercero': form_ter,
        'formset':      formset,
        'modo':         'editar',
        'reserva':      reserva,
    })

@login_required
def eliminar_reserva(request, pk):
    reserva = get_object_or_404(Reserva, pk=pk)
    if request.method == 'POST':
        # al eliminar devolvemos stock
        for item in reserva.items.all():
            prod = item.producto
            prod.existencias += item.cantidad
            prod.save()
        reserva.delete()
        return redirect('reserva_list')
    return render(request, 'productos/reservas/confirm_delete.html', {'object': reserva})


# ——— GESTIÓN DE USUARIOS ———
class UsuarioListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = Usuario
    template_name = 'productos/catalogos/usuario/list.html'
    context_object_name = 'usuarios'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object_list'] = []  # Empty list for server-side processing
        return context

def usuario_datatable_view(request):
    """Vista AJAX para DataTables de usuarios"""
    # Parámetros de DataTables
    draw = int(request.GET.get('draw', 1))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 25))
    search_value = request.GET.get('search[value]', '')
    order_column = int(request.GET.get('order[0][column]', 1))
    order_dir = request.GET.get('order[0][dir]', 'asc')

    # Columnas para ordenamiento
    columns = ['id', 'username', 'first_name', 'last_name', 'email', 'rol__nombre', 'activo', 'date_joined']

    # Query base
    queryset = Usuario.objects.select_related('rol')

    # Filtro de búsqueda
    if search_value:
        queryset = queryset.filter(
            Q(username__icontains=search_value) |
            Q(first_name__icontains=search_value) |
            Q(last_name__icontains=search_value) |
            Q(email__icontains=search_value) |
            Q(rol__nombre__icontains=search_value)
        )

    # Total de registros
    total_records = Usuario.objects.count()
    filtered_records = queryset.count()

    # Ordenamiento
    if 0 <= order_column < len(columns):
        order_field = columns[order_column]
        if order_dir == 'desc':
            order_field = f'-{order_field}'
        queryset = queryset.order_by(order_field)
    else:
        queryset = queryset.order_by('-date_joined')

    # Paginación
    usuarios = queryset[start:start + length]

    # Preparar datos
    data = []
    for usuario in usuarios:
        # Estado del usuario
        if usuario.puede_acceder():
            estado_badge = '<span class="badge bg-success">Activo</span>'
        elif usuario.activo and usuario.is_active:
            estado_badge = '<span class="badge bg-warning text-dark">Sin Permisos</span>'
        else:
            estado_badge = '<span class="badge bg-danger">Inactivo</span>'
        
        # Rol
        rol_text = usuario.rol.nombre if usuario.rol else 'Sin rol'
        
        # Botones de acción
        actions = f'''
            <div class="btn-group" role="group">
                <a href="{reverse('usuario_update', args=[usuario.id])}" 
                   class="btn btn-sm btn-warning" title="Editar">
                    <i class="fas fa-edit"></i>
                </a>
        '''
        
        # Solo mostrar eliminar si no es el usuario actual
        if usuario.id != request.user.id:
            actions += f'''
                <a href="{reverse('usuario_delete', args=[usuario.id])}" 
                   class="btn btn-sm btn-danger" title="Eliminar">
                    <i class="fas fa-trash"></i>
                </a>
            '''
        
        actions += '</div>'

        data.append([
            usuario.id,
            usuario.username,
            usuario.first_name or '',
            usuario.last_name or '',
            usuario.email,
            rol_text,
            estado_badge,
            usuario.date_joined.strftime('%d/%m/%Y'),
            actions
        ])

    return JsonResponse({
        'draw': draw,
        'recordsTotal': total_records,
        'recordsFiltered': filtered_records,
        'data': data
    })

class UsuarioUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = Usuario
    form_class = UsuarioGestionForm
    template_name = 'productos/catalogos/usuario/form.html'
    success_url = reverse_lazy('usuario_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Usuario {form.instance.username} actualizado correctamente.')
        return super().form_valid(form)

class UsuarioDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    model = Usuario
    template_name = 'productos/catalogos/usuario/confirm_delete.html'
    success_url = reverse_lazy('usuario_list')
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        # Prevenir que el usuario se elimine a sí mismo
        if obj.id == self.request.user.id:
            from django.http import Http404
            raise Http404("No puedes eliminar tu propia cuenta")
        return obj
    
    def delete(self, request, *args, **kwargs):
        usuario = self.get_object()
        username = usuario.username
        response = super().delete(request, *args, **kwargs)
        messages.success(request, f'Usuario {username} eliminado correctamente.')
        return response

@login_required
def acceso_denegado_view(request):
    """Vista para usuarios logueados pero sin permisos"""
    # Si el usuario puede acceder, redirigir al home
    if request.user.puede_acceder():
        return redirect('home')
    
    context = {
        'user': request.user,
        'puede_acceder': request.user.puede_acceder(),
        'rol_nombre': request.user.rol.nombre if request.user.rol else 'Sin rol',
    }
    return render(request, 'productos/acceso_denegado.html', context)