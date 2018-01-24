
from django.utils.translation import ugettext as _, ugettext_lazy
from django.shortcuts import redirect  
from django.urls import reverse

def merge_records(model_admin, request, queryset):
    if queryset.count()==1:
        model_admin.message_user(request,'Es müssen mindestens zwei Objekte aus der Liste ausgewählt werden, um diese Aktion durchzuführen', 'warning')
        return
    if not model_admin.merge_allowed(request, queryset):
        return
    request.session['merge'] = {'qs_ids': list(queryset.values_list('pk', flat=True)), 'success_url' : request.get_full_path()}
    return redirect(reverse('merge', kwargs=dict(model_name=model_admin.opts.model_name)))
merge_records.short_description = ugettext_lazy("Merge selected %(verbose_name_plural)s")#'Datensätze zusammenfügen'
merge_records.perm_required = 'merge'
