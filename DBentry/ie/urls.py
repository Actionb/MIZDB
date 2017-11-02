#
from django.conf.urls import url
from .views import *

import_urls = [
        url(r'^discogs_import/$',ImportSelectView.as_view(), name='import_select'),
    ]

