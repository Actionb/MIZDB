from django.core.management.base import BaseCommand, CommandError

from DBentry.base.models import ComputedNameModel
from django.apps import apps

class Command(BaseCommand):
    
    requires_migrations_checks = True
    
    help = 'Updates the name attribute of all models subclassing ComputedNameModel.'

    def add_arguments(self, parser):
        parser.add_argument('-f','--force',action='store_true', help='Force the update of all models.')
   
    def handle(self, *args, **options):
       CNmodels = [m for m in apps.get_models('DBentry') if ComputedNameModel in m.mro()]
       for model in CNmodels:
           if options['force']:
               model.objects.update(_changed_flag=True)
           model.objects.all()._update_names()
           self.stdout.write("{} updated!".format(model._meta.verbose_name))
