from django import http
from django.contrib.auth import get_permission_codename
from django.utils.translation import gettext

from dal import autocomplete

from DBentry.ac.creator import Creator
from DBentry.models import ausgabe, buch
from DBentry.logging import LoggingMixin
from DBentry.utils import get_model_from_string


class ACBase(autocomplete.Select2QuerySetView, LoggingMixin):
    """Base view for the autocomplete views of the DBentry app."""

    def dispatch(self, *args, **kwargs):
        if not self.model:
            model_name = kwargs.pop('model_name', '')
            self.model = get_model_from_string(model_name)
        if self.create_field is None:
            self.create_field = kwargs.pop('create_field', None)
        return super().dispatch(*args, **kwargs)

    def has_create_field(self):
        if self.create_field:
            return True
        return False

    def display_create_option(self, context, q):
        """
        Return a boolean whether the create option should be displayed or not.
        """
        if self.has_create_field() and q:
            page_obj = context.get('page_obj', None)
            if page_obj is None or not self.has_more(context):
                return True
        return False

    def build_create_option(self, q):
        return [{
            'id': q,
            'text': gettext('Create "%(new_value)s"') % {'new_value': q},
            'create_id': True,
        }]

    def get_create_option(self, context, q):
        """Form the correct create_option to append to results."""
        if (self.display_create_option(context, q)
                and self.has_add_permission(self.request)):
            return self.build_create_option(q)
        return []

    def do_ordering(self, qs):
        # FIXME: reapplying the model's default ordering could remove ordering
        # set by a declared MultipleObjectMixin.queryset attribute.
        return qs.order_by(*self.model._meta.ordering)

    def apply_q(self, qs):
        """Filter the given queryset 'qs' with the view's search term 'q'."""
        if self.q:
            return qs.find(self.q)
        else:
            return qs

    def create_object(self, text):
        """Create an object given a text."""
        obj = self.model.objects.create(**{self.create_field: text})
        if obj and self.request:
            self.log_addition(obj)
        return obj

    def get_queryset(self):
        """Return the ordered and filtered queryset for this view."""
        # TODO: rely on MultipleObjectMixin.get_queryset ?
        if self.queryset is None:
            qs = self.model.objects.all()
        else:
            qs = self.queryset

        if self.forwarded:
            forward_filter = {}
            for k, v in self.forwarded.items():
                # Remove 'empty' forward items.
                if k and v:
                    forward_filter[k] = v
            if not forward_filter:
                # All forwarded items were empty; return an empty queryset.
                return self.model.objects.none()
            qs = qs.filter(**forward_filter)

        qs = self.do_ordering(qs)
        qs = self.apply_q(qs)
        return qs

    def has_add_permission(self, request):
        """Return True if the user has the permission to add a model."""
        if not request.user.is_authenticated:
            return False
        # At this point, dal calls get_queryset() to get the model options via
        # queryset.model._meta which is unnecessary for ACBase since it
        # declares the model class during dispatch().
        opts = self.model._meta
        codename = get_permission_codename('add', opts)
        return request.user.has_perm("%s.%s" % (opts.app_label, codename))

    def get_result_value(self, result):
        """Return the value of a result."""
        if isinstance(result, (list, tuple)):
            if result[0] == 0:
                # The list 'result' contains the IDs of the results.
                # A '0' ID may be the 'weak hits' separator
                # (query.PrimaryFieldsSearchQuery).
                # Set it's id to None to make it unselectable.
                return None
            return result[0]
        return str(result.pk)

    def get_result_label(self, result):
        """Return the label of a result."""
        if isinstance(result, (list, tuple)):
            return result[1]
        return str(result)


class ACBuchband(ACBase):
    """
    Autocomplete view that queries buch instances that are defined as 'buchband'.
    """

    model = buch
    queryset = buch.objects.filter(is_buchband=True)


class ACAusgabe(ACBase):
    """
    Autocomplete view for the model ausgabe that applies chronologic order to
    the results.
    """

    model = ausgabe

    def do_ordering(self, qs):
        return qs.chronologic_order()


class ACCreateable(ACBase):
    """
    Add additional information to the create_option part of the response and
    enable a more involved model instance creation process by utilizing a
    Creator helper object.
    """

    @property
    def creator(self):
        if not hasattr(self, '_creator'):
            self._creator = Creator(self.model, raise_exceptions=False)
        return self._creator

    def createable(self, text, creator=None):
        """
        Return True if a new(!) model instance would be created from 'text'.
        """
        creator = creator or self.creator
        created = creator.create(text, preview=True)
        pk = getattr(created.get('instance', None), 'pk', None)
        if created and pk is None:
            return True
        return False

    def display_create_option(self, context, q):
        """
        Return a boolean whether the create option should be displayed or not.
        """
        if q:
            page_obj = context.get('page_obj', None)
            if page_obj is None or not self.has_more(context):
                # See if we can create a new object from q.
                # If pre-existing objects can be found using q, the create
                # option should not be enabled.
                if self.createable(q):
                    return True
        return False

    def build_create_option(self, q):
        """
        Add additional information on how the object is going to be created
        to the create option.
        """
        create_option = super().build_create_option(q)
        create_info = self.get_creation_info(q)
        if create_info:
            create_option.extend(create_info)
        return create_option

    def get_creation_info(self, text, creator=None):
        """
        Build template context to display a more informative create option.
        """
        def flatten_dict(_dict):
            rslt = []
            for k, v in _dict.items():
                if not v or k == 'instance':
                    continue
                if isinstance(v, dict):
                    rslt.extend(flatten_dict(v))
                else:
                    rslt.append((k, v))
            return rslt

        creator = creator or self.creator
        create_info = []
        default = {
            'id': None,  # 'id': None will make the option unselectable.
            'create_id': True, 'text': '...mit folgenden Daten:'
        }

        create_info.append(default.copy())
        # Iterate over all nested dicts in create_info returned by the creator.
        for k, v in flatten_dict(creator.create(text, preview=True)):
            default['text'] = str(k) + ': ' + str(v)
            create_info.append(default.copy())
        return create_info

    def create_object(self, text, creator=None):
        """Create a model instance from 'text' and save it to the database."""
        if self.has_create_field():
            return super().create_object(text)
        creator = creator or self.creator
        return creator.create(text, preview=False).get('instance')

    def post(self, request):
        """Create an object given a text after checking permissions."""
        if not self.has_add_permission(request):
            return http.HttpResponseForbidden()

        if not self.creator and not self.create_field:
            raise AttributeError('Missing creator object or "create_field"')

        text = request.POST.get('text', None)

        if text is None:
            return http.HttpResponseBadRequest()

        try:
            result = self.create_object(text)
        except:
            msg = 'Erstellung fehlgeschlagen. Bitte benutze den "Hinzufügen" Knopf.'
            return http.JsonResponse({'id': 0, 'text': msg})

        return http.JsonResponse({'id': result.pk, 'text': str(result)})
