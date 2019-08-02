from django import views

from DBentry import models as _models
from DBentry.base.views import MIZAdminToolViewMixin, PERM_DENIED_MSG
from DBentry.forms import FavoritenForm
from DBentry.sites import miz_site, register_tool


@register_tool
class FavoritenView(MIZAdminToolViewMixin, views.generic.UpdateView):
    form_class = FavoritenForm
    template_name = 'admin/favorites.html'
    model = _models.Favoriten

    url_name = 'favoriten'
    index_label = 'Favoriten Verwaltung'

    _permissions_required = [('add', 'Favoriten'), ('change', 'Favoriten'), ('delete', 'Favoriten')]

    def get_success_url(self):
        # Redirect back onto this site
        return ''

    def get_object(self):
        # user field on Favoriten is unique, so at most a single user can have one set of favorites or none
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
    try:
        template = loader.get_template(template_name)
    except TemplateDoesNotExist:
        return http.HttpResponseForbidden('<h1>403 Forbidden</h1>', content_type='text/html')

    from django.template.response import TemplateResponse
    context = {'exception' : str(exception) if str(exception) else PERM_DENIED_MSG}
    context.update(miz_site.each_context(request))
    context['is_popup'] = '_popup' in request.GET 
    return TemplateResponse(request, template_name, context=context)
