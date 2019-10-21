from django import views
from django.contrib.auth.mixins import PermissionRequiredMixin

from DBentry import models as _models
from DBentry.base.views import MIZAdminMixin
from DBentry.forms import FavoritenForm
from DBentry.sites import miz_site, register_tool


@register_tool(url_name='favoriten', index_label='Favoriten Verwaltung')
class FavoritenView(MIZAdminMixin, PermissionRequiredMixin, views.generic.UpdateView):
    form_class = FavoritenForm
    template_name = 'admin/favorites.html'
    model = _models.Favoriten

    permission_required = [
        'DBentry.add_favoriten',
        'DBentry.change_favoriten',
        'DBentry.delete_favoriten'
    ]

    def get_success_url(self):
        # Redirect back to this site.
        return ''

    def get_object(self):
        # user field on Favoriten is unique, so at most a single user can have
        # one set of favorites or none.
        object = self.model.objects.filter(user=self.request.user).first()
        if object is None:
            # user has no favorites yet, create an entry in Favoriten model
            object = self.model(user=self.request.user)
            object.save()
        return object


# views for the django default handlers
def MIZ_permission_denied_view(request, exception, template_name='admin/403.html'):
    from django.template import TemplateDoesNotExist, loader
    from django import http
    # Make sure that a template for template_name exists.
    try:
        template = loader.get_template(template_name)
    except TemplateDoesNotExist:
        return http.HttpResponseForbidden(
            '<h1>403 Forbidden</h1>', content_type='text/html')

    from django.template.response import TemplateResponse
    msg = 'Sie haben nicht die erforderliche Berechtigung diese Seite zu sehen.'
    context = {'exception': str(exception) if str(exception) else msg}
    context.update(miz_site.each_context(request))
    context['is_popup'] = '_popup' in request.GET
    return TemplateResponse(request, template_name, context=context)
