from django.conf.urls import url,  include

urlpatterns = [
    url(r'',  include('DBentry.ac.urls'))
]

from .views import BulkAusgabe
admin_tools_urls = [
    url(r'^bulk_ausgabe/$', BulkAusgabe.as_view(), name='bulk_ausgabe'), 
]
