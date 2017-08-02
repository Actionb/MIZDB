from django.contrib.admin.filters import RelatedOnlyFieldListFilter
from django_admin_listfilter_dropdown.filters import DropdownFilter, RelatedDropdownFilter

class DependDropdownFilter(DropdownFilter):
    pass
    
    
class ArtikelAusgabeFilter(DropdownFilter):
    title = 'Nach Ausgabe'
    
class RelatedOnlyDropdownFilter(RelatedOnlyFieldListFilter):
    template = 'django_admin_listfilter_dropdown/dropdown_filter.html'
    
