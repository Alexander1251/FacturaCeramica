# dte/migrations/0002_factura_campos_hacienda.py
# Ejecutar: python manage.py makemigrations y luego python manage.py migrate

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dte', '0001_initial'),  # Ajustar según tu migración anterior
    ]

    operations = [
        migrations.AddField(
            model_name='facturaelectronica',
            name='documento_firmado',
            field=models.TextField(blank=True, help_text='Documento DTE firmado en formato JWS', null=True),
        ),
        migrations.AddField(
            model_name='facturaelectronica',
            name='sello_recepcion',
            field=models.CharField(blank=True, help_text='Sello de recepción otorgado por Hacienda', max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='facturaelectronica',
            name='fecha_procesamiento',
            field=models.CharField(blank=True, help_text='Fecha y hora de procesamiento en Hacienda', max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='facturaelectronica',
            name='estado_hacienda',
            field=models.CharField(
                choices=[
                    ('PENDIENTE', 'Pendiente de envío'),
                    ('ENVIADO', 'Enviado a Hacienda'),
                    ('ACEPTADO', 'Aceptado por Hacienda'),
                    ('RECHAZADO', 'Rechazado por Hacienda'),
                    ('CONTINGENCIA', 'En contingencia'),
                ],
                default='PENDIENTE',
                help_text='Estado del documento en Hacienda',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='facturaelectronica',
            name='observaciones_hacienda',
            field=models.TextField(blank=True, help_text='Observaciones o errores reportados por Hacienda', null=True),
        ),
        migrations.AddField(
            model_name='facturaelectronica',
            name='fecha_envio_hacienda',
            field=models.DateTimeField(blank=True, help_text='Fecha y hora de envío a Hacienda', null=True),
        ),
        migrations.AddField(
            model_name='facturaelectronica',
            name='intentos_envio',
            field=models.IntegerField(default=0, help_text='Número de intentos de envío realizados'),
        ),
        migrations.AddField(
            model_name='facturaelectronica',
            name='enviado_por_correo',
            field=models.BooleanField(default=False, help_text='Indica si fue enviado por correo al receptor'),
        ),
        migrations.AddField(
            model_name='facturaelectronica',
            name='fecha_envio_correo',
            field=models.DateTimeField(blank=True, help_text='Fecha y hora de envío por correo', null=True),
        ),
    ]