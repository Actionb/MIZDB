from django.apps import apps
from django.core.management.base import BaseCommand

from dbentry.base.models import ComputedNameModel


class Command(BaseCommand):
    requires_migrations_checks = True

    help = (
        'Updates the name attribute of all model instances of models '
        'subclassing ComputedNameModel.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '-f', '--force',
            action='store_true',
            help='Force the update of all model instances.'
        )

    def handle(self, *args, **options):
        models = [
            model
            for model in apps.get_models('dbentry')
            if issubclass(model, ComputedNameModel)
        ]
        for model in models:
            if options['force']:
                model.objects.update(_changed_flag=True)
            model.objects.all()._update_names()
            # noinspection PyUnresolvedReferences
            self.stdout.write("{} updated!".format(model._meta.verbose_name))
