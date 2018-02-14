from django import forms
from .base import *

from DBentry.views import *
from DBentry.maint.views import *
from DBentry.ie.views import *
from DBentry.ac.views import *

def setup_wizard_view(view, request, *args, **kwargs):
    #TODO: this looks WRONG
    view.request = request
    for k, v in view.get_initkwargs().items():
        setattr(view, k, v)
    view.args = args
    view.kwargs = kwargs
    view.dispatch(request, **view.kwargs) # WizardView sets a couple of attributes during dispatch (steps,storage,...)
    return view
    
class TestOptionalFormView(ViewTestCase):
    
    view_class = OptionalFormView
    form_class = forms.Form
    
    def test_get_form(self):
        # OptionalFormView should return a form of the given form_class
        view = self.view(request=self.get_request(), form_class=self.form_class)
        self.assertIsInstance(view.get_form(), forms.Form)
        
    def test_get_form_no_formclass(self):
        # If no form_class is set (i.e. the form is optional), get_form() should return None
        view = self.view()
        self.assertIsNone(view.get_form())
        
        # Pass a dummy form_class to get_form(), it should still prioritize being optional
        self.assertIsNone(view.get_form(self.form_class))
        
    def test_post_form_is_none(self):
        # Test that the post method acknowledges the optional form
        request = self.post_request()
        view = self.view(request, success_url='Test')
        response = view.post(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, 'Test')

class TestMIZAdminToolView(ViewTestCase):
    # includes tests for the mixins: MIZAdminMixin, MIZAdminPermissionMixin
    
    view_class = MIZAdminToolView
    
    def test_permission_test_only_staff_required(self):
        # basic test for user.is_staff as MIZAdminToolView does not set any required permissions
        request = self.get_request(user=self.noperms_user)
        self.assertFalse(self.view(request).permission_test())
        self.assertFalse(self.view_class.show_on_index_page(request))
        
        request = self.get_request(user=self.staff_user)
        self.assertTrue(self.view(request).permission_test())
        self.assertTrue(self.view_class.show_on_index_page(request))
        
        request = self.get_request()
        self.assertTrue(self.view(request).permission_test())
        self.assertTrue(self.view_class.show_on_index_page(request))
        
    def test_permission_test_with_explicit_permreq(self):
        # setting MIZAdminToolView.permission_required 
        # none of the users actually have any permissions set other than is_staff/is_superuser
        perm = ['beepboop']
        request = self.get_request(user=self.noperms_user)
        view = self.view(request, permissions_required=perm)
        self.assertFalse(view.permission_test())
        
        request = self.get_request(user=self.staff_user)
        view = self.view(request, permissions_required=perm)
        self.assertFalse(view.permission_test())
        
        request = self.get_request()
        view = self.view(request, permissions_required=perm)
        self.assertTrue(view.permission_test())
        
    def test_permissions_required_cached_prop(self):
        # setting MIZAdminToolView._permission_required, forcing the cached_property permission_required
        perm = ['perm1', ('perm2', ), ('perm3', ausgabe), ('perm4', 'ausgabe')]
        expected = ['DBentry.perm1_ausgabe', 'DBentry.perm2_ausgabe', 'DBentry.perm3_ausgabe', 'DBentry.perm4_ausgabe']
        # opts set on view
        view = self.view(self.get_request(), _permissions_required=perm)
        view.opts = ausgabe._meta
        self.assertEqual(view.permissions_required, expected)        
        
        # model set on view
        view = self.view(self.get_request(), _permissions_required=perm)
        view.model = ausgabe
        self.assertEqual(view.permissions_required, expected)      
        
        # no opts/model set on view => ImproperlyConfigured exception
        view = self.view(self.get_request(), _permissions_required=perm)
        from django.core.exceptions import ImproperlyConfigured
        with self.assertRaises(ImproperlyConfigured):
            view.permissions_required
        
    def test_get_context_data(self):
        request = self.get_request()
        context_data = self.view(request).get_context_data()
        self.assertTrue('submit_value' in context_data and 'submit_name' in context_data)
        self.assertEqual(context_data.get('is_popup', False), False)
        
        request = self.get_request(data={'_popup':1})
        context_data = self.view(request).get_context_data()
        self.assertEqual(context_data.get('is_popup', False), True)
    
class TestFavoritenView(ViewTestCase):
    
    view_class = FavoritenView
    
    def test_get_success_url(self):
        request = self.get_request()
        view = self.view(request)
        self.assertEqual(view.get_success_url(), '')
    
    def test_get_object(self):
        request = self.get_request()
        view = self.view(request)
        self.assertFalse(view.model.objects.filter(user=request.user).exists())
        self.assertEqual(view.get_object().user, self.super_user) # user has no Favoriten yet, create an entry in Favoriten
        self.assertTrue(view.model.objects.filter(user=request.user).exists())
        self.assertEqual(view.get_object().user, self.super_user) # direct access to Favoriten via queryset
        
class TestACBase(ACViewTestCase):
    
    view_class = ACBase
    path = reverse('acband')
    model = band
    create_field = 'band_name'

    @classmethod
    def setUpTestData(cls):
        super(TestACBase, cls).setUpTestData()
        cls.obj1 = band.objects.create(band_name='Boop')
        cls.genre = genre.objects.create(genre='Testgenre')
        m2m_band_genre.objects.create(band=cls.obj1, genre=cls.genre)
        cls.musiker = musiker.objects.create(kuenstler_name='Meehh')
        m2m_band_musiker.objects.create(band=cls.obj1, musiker=cls.musiker)
        cls.obj2 = band.objects.create(band_name='leboop')
        cls.obj3 = band.objects.create(band_name='notfound')
        cls.obj4 = band.objects.create(band_name='Boopband')
    
    def test_has_create_field(self):
        v = self.view()
        self.assertTrue(v.has_create_field())
        v.create_field = ''
        self.assertFalse(v.has_create_field())
        
    def test_create_object_no_log_entry(self):
        # no request set on view, no log entry should be created
        obj = self.view().create_object('Beep')
        from django.contrib.admin.models import LogEntry
        qs = LogEntry.objects.filter(object_id=obj.pk)
        self.assertFalse(qs.exists())
        
    def test_create_object_with_log_entry(self):
        # request set on view, log entry should be created
        request = self.get_request()
        obj = self.view(request).create_object('Boop')
        from django.contrib.admin.models import LogEntry
        qs = LogEntry.objects.filter(object_id=obj.pk)
        self.assertTrue(qs.exists())
        
    def test_get_create_option(self):
        request = self.get_request()
        create_option = self.view(request).get_create_option(context={}, q='Beep')
        self.assertEqual(len(create_option), 1)
        self.assertEqual(create_option[0].get('id'), 'Beep')
        self.assertEqual(create_option[0].get('text'), 'Erstelle "Beep"')
        self.assertTrue(create_option[0].get('create_id'))
        
    def test_get_create_option_no_create_field(self):
        request = self.get_request()
        view = self.view(request)
        view.create_field = ''
        create_option = view.get_create_option(context={}, q='')
        self.assertEqual(create_option, [])
        
    def test_get_create_option_no_perms(self):
        request = self.get_request(user=self.noperms_user)
        create_option = self.view(request).get_create_option(context={}, q='Beep')
        self.assertEqual(create_option, [])
    
    @skip('Needs to be reworked anyhow. Should default to model.get_search_fields')
    def test_flds_prop(self):
        # Check if flds removes fields that are not part of the model
        self.model.search_fields = ['beep']
        self.assertFalse('beep' in self.view().flds)
        
    def test_do_ordering(self):
        # Test covered by test_get_queryset
        pass
        
    def test_apply_q(self):
        view = self.view(q='Boop')
        exact_match_qs = [self.obj1]
        
        startswith_qs = [self.obj1, self.obj4]
        
        contains_qs = [self.obj1, self.obj4, self.obj2]
        
        self.assertEqual(list(view.apply_q(self.model.objects.all())), contains_qs)
        
    def test_apply_q_favorites(self):
        fav = Favoriten.objects.create(user=self.super_user)
        fav.fav_genres.add(self.genre)
        first_genre = genre.objects.create(genre='A')
        request = self.get_request()
        view = self.view(request=request, model=genre)
        self.assertTrue(Favoriten.objects.filter(user=view.request.user).exists())
        self.assertEqual(list(view.apply_q(genre.objects.all())), [self.genre, first_genre, self.genre])
        
    def test_get_queryset(self):
        request = self.get_request()
        view = self.view(request)
        view.q = 'notfound'
        self.assertEqual(list(view.get_queryset()), [self.obj3])
        
    def test_get_queryset_no_q(self):
        request = self.get_request()
        view = self.view(request)
        self.assertEqual(list(view.get_queryset()), [self.obj1, self.obj4, self.obj2, self.obj3])
        
    def test_get_queryset_forwarded(self):
        # fake forwarded attribute
        request = self.get_request()
        view = self.view(request)
        view.forwarded = {'genre':self.genre.pk, 'TROUBLES__musiker':self.musiker.pk}
        self.assertEqual(list(view.get_queryset()), [self.obj1])
        
        view.forwarded = {'':'ignore_me'}
        self.assertFalse(view.get_queryset().exists())
        
    def test_has_add_permission(self):
        # Test largely covered by test_get_create_option_no_perms
        self.client.logout()
        request = self.get_request()
        # Seems I cannot log out? Assertion fails. Need to be NOT authenticated, i.e. AnonymousUser
        #self.assertFalse(self.view().has_add_permission(request)) 
        
class TestACProv(ACViewTestCase):
    
    view_class = ACProv
    path = reverse('acprov')
    model = provenienz
    
    def test_has_create_field(self):
        self.assertTrue(self.view().has_create_field())
        
    def test_create_object_no_log_entry(self):
        obj = self.view().create_object('Beep')
        self.assertEqual(obj.geber.name, 'Beep')
        from django.contrib.admin.models import LogEntry
        qs = LogEntry.objects.filter(object_id=obj.pk)
        self.assertFalse(qs.exists())
        
        
    def test_create_object_with_log_entry(self):
        request = self.get_request()
        obj = self.view(request).create_object('Beep')
        from django.contrib.admin.models import LogEntry
        qs = LogEntry.objects.filter(object_id=obj.pk)
        self.assertTrue(qs.exists())
        
        
class TestACAusgabe(ACViewTestCase):
    
    view_class = ACAusgabe
    path = reverse('acausgabe')
    model = ausgabe
    
    @classmethod
    def setUpTestData(cls):
        super(TestACAusgabe, cls).setUpTestData()
        cls.mag = magazin.objects.create(magazin_name='Testmagazin')
        cls.obj_num = ausgabe.objects.create(magazin=cls.mag)
        cls.obj_num.ausgabe_jahr_set.create(jahr=2020)
        cls.obj_num.ausgabe_num_set.create(num=10)
        
        cls.obj_lnum = ausgabe.objects.create(magazin=cls.mag)
        cls.obj_lnum.ausgabe_jahr_set.create(jahr=2020)
        cls.obj_lnum.ausgabe_lnum_set.create(lnum=10)
        
        cls.obj_monat = ausgabe.objects.create(magazin=cls.mag)
        cls.obj_monat.ausgabe_jahr_set.create(jahr=2020)
        cls.obj_monat.ausgabe_monat_set.create(monat=monat.objects.create(id=1, monat='Januar', abk='Jan'))
        
        cls.obj_sonder = ausgabe.objects.create(magazin=cls.mag, sonderausgabe=True, info='Special Edition')
        
        cls.obj_jahrg = ausgabe.objects.create(magazin=cls.mag, jahrgang=12)
        cls.obj_jahrg.ausgabe_num_set.create(num=13)
        
    def setUp(self):
        super(TestACAusgabe, self).setUp()
        self.qs = self.model.objects.all()
    
    def test_do_ordering(self):
        pass
        
    def test_apply_q_num(self):
        view = self.view(q=self.obj_num.__str__())
        expected_qs = list(self.qs.filter(pk=self.obj_num.pk))
        self.assertEqual(list(view.apply_q(self.qs)), expected_qs)
        
        self.obj_num.ausgabe_num_set.create(num=11)
        view = self.view(q=self.obj_num.__str__())
        self.assertEqual(list(view.apply_q(self.qs)), expected_qs)
        
    def test_apply_q_lnum(self):
        view = self.view(q=self.obj_lnum.__str__())
        expected_qs = list(self.qs.filter(pk=self.obj_lnum.pk))
        self.assertEqual(list(view.apply_q(self.qs)), expected_qs)
        
        self.obj_lnum.ausgabe_lnum_set.create(lnum=11)
        view = self.view(q=self.obj_lnum.__str__())
        self.assertEqual(list(view.apply_q(self.qs)), expected_qs)
        
    def test_apply_q_monat(self):
        view = self.view(q=self.obj_monat.__str__())
        expected_qs = list(self.qs.filter(pk=self.obj_monat.pk))
        self.assertEqual(list(view.apply_q(self.qs)), expected_qs)
        
        self.obj_monat.ausgabe_monat_set.create(monat=monat.objects.create(id=2, monat='Februar', abk='Feb'))
        view = self.view(q=self.obj_monat.__str__())
        self.assertEqual(list(view.apply_q(self.qs)), expected_qs)
        
    def test_apply_q_sonderausgabe_forwarded(self):
        view = self.view(q=self.obj_sonder.__str__(), forwarded={'magazin':self.mag.pk})
        expected_qs = list(self.qs.filter(pk=self.obj_sonder.pk))
        self.assertEqual(list(view.apply_q(self.qs)), expected_qs)
        
    #NOTE: ausgabe.strquery / apply_q does not work with sonderausgabe or jahrgang (yet)
    @expectedFailure
    def test_apply_q_sonderausgabe(self):
        view = self.view(q=self.obj_sonder.__str__())
        expected_qs = list(self.qs.filter(pk=self.obj_sonder.pk))
        self.assertEqual(list(view.apply_q(self.qs)), expected_qs)
        
    @expectedFailure
    def test_apply_q_jahrgang(self):
        view = self.view(q=self.obj_jahrg.__str__())
        expected_qs = list(self.qs.filter(pk=self.obj_jahrg.pk))
        self.assertEqual(list(view.apply_q(self.qs)), expected_qs)
        
class TestPermissionDeniedView(TestCase):
    
    def test_MIZ_permission_denied_view_missing_template(self):
        response = MIZ_permission_denied_view(None, None, template_name='beepboop')
        from django import http
        self.assertTrue(isinstance(response, http.HttpResponseForbidden))
    
    def test_MIZ_permission_denied_view(self):
        from django.core.exceptions import PermissionDenied
        exception = PermissionDenied('Exception Text')
        request = self.client.get('').wsgi_request
        response = MIZ_permission_denied_view(request, exception)
        self.assertTrue('exception' in response.context_data)
        self.assertEqual(response.context_data['exception'], 'Exception Text')
        
        self.assertTrue('is_popup' in response.context_data)
