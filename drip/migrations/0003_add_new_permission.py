from django.db import migrations
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission, Group

CAN_ADD_DRIP = 'can_edit_drip_queryset'


def install_permission(apps, schema_editor):
    Drip = apps.get_model('drip', 'Drip')
    content_type = ContentType.objects.get_for_model(Drip)
    group = Group.objects.get_or_create(name='Drip Admin')
    perm, created = Permission.objects.get_or_create(
        codename=CAN_ADD_DRIP,
        content_type=content_type
    )
    group[0].permissions.add(perm)
    if created:
        perm.name = 'Can edit drip queryset'
        perm.save()


def revert_install_permission(apps, schema_editor):
    Group.objects.filter(name='Drip Admin').delete()
    Permission.objects.filter(codename=CAN_ADD_DRIP).delete()



class Migration(migrations.Migration):

    dependencies = [
        ('drip', '0002_auto_20201021_1223'),
    ]

    operations = [
        migrations.RunPython(install_permission, revert_install_permission),
    ]
