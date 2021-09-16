"""
A Django Management Command to rename 'DBentry' app to 'dbentry'.
Based on: https://github.com/odwyersoftware/django-rename-app
"""

import logging

from django.core.management.base import BaseCommand
from django.db import ProgrammingError, connection

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        'Renames the DBentry application to dbentry.'
    )

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE django_content_type SET app_label='dbentry' "
                "WHERE app_label='DBentry'"
            )
            cursor.execute(
                "UPDATE django_migrations SET app='dbentry' "
                "WHERE app='DBentry'"
            )
            # Get the names of the tables that start with 'DBentry'.
            cursor.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_name LIKE 'DBentry%'"
            )
            try:
                for table_name in cursor.fetchall():
                    query = (
                        'ALTER TABLE "{old_table_name}" '
                        'RENAME TO "{new_table_name}"'.format(
                            old_table_name=table_name[0],
                            new_table_name=table_name[0].lower()
                        )
                    )
                    try:
                        cursor.execute(query)
                    except ProgrammingError:
                        logger.warning(
                            'Rename query failed: "%s"', query, exc_info=True
                        )
            except ProgrammingError:
                # The table names query returned no results.
                pass
