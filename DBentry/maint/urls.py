from django.urls import path
from DBentry.maint.views import DuplicateObjectsView, ModelSelectView

urlpatterns = [
    path('dupes/<str:model_name>/', DuplicateObjectsView.as_view(), name = 'dupes'), 
    #TODO: path('unused/<str:model_name>/lte<int:lte>/', UnusedObjectsView.as_view(), name = 'unused_objects'), 
    path('dupes/', ModelSelectView.as_view(title='Duplikate', next_view = 'dupes'), name='dupes_select'), 
    #TODO: path('unused/', ModelSelectView.as_view(title='Unbenutzt', next_view = 'unused_objects'), name='unused_select'), 
    #TODO: path('', MaintView.as_view(), name='maint_index'),
]
