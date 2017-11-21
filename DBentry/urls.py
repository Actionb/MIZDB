from django.conf.urls import url,  include


from .views import BulkAusgabe

admin_tools_urls = [
    url(r'^bulk_ausgabe/$', BulkAusgabe.as_view(), name='bulk_ausgabe'), 
    url(r'', include('DBentry.ie.urls'))
]

urlpatterns = [
    url(r'^ac/',  include('DBentry.ac.urls')), 
    url(r'^tools/', include(admin_tools_urls))
]
