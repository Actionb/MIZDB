from django.urls import reverse, resolve

from .base import *

from DBentry.views import *
from DBentry.maint.views import *
from DBentry.ie.views import *
from DBentry.ac.views import *
from DBentry.bulk.views import *


def setup_view(view, request=None, args=None, kwargs=None):
    # return view class 
    view.request = request
    view.args = args
    view.kwargs = kwargs
    return view
    
def setup_wizard_view(view, request, *args, **kwargs):
    view.request = request
    for k, v in view.get_initkwargs().items():
        setattr(view, k, v)
    view.args = args
    view.kwargs = kwargs
    view.dispatch(request, **view.kwargs) # WizardView sets a couple of attributes during dispatch (steps,storage,...)
    return view

class BaseTestView(UserTestCase):
    
    view_class = None
    path = ''
    
    def view(self, request=None, args=None, kwargs=None, **initkwargs):
        self.view_class.request = request
        self.view_class.args = args
        self.view_class.kwargs = kwargs
        return self.view_class(**initkwargs)
        
    def post_request(self, path='', data={}, user=None):
        self.client.force_login(user or self.super_user)
        return self.client.post(path or self.path, data).wsgi_request
    
    def get_request(self, path='', data={}, user=None):
        self.client.force_login(user or self.super_user)
        return self.client.get(path or self.path, data).wsgi_request
        
class BaseFormViewMixin(object):
    
    form_class = None
    
    def get_form(self, data = None, files = None, initial = None):
        if hasattr(self, 'valid_data'):
            data = getattr(self, 'valid_data', {}).copy()
        if getattr(self, 'view_class', None) is not None:
            if getattr(self.view_class, 'form_class', None) is not None:
                form_class = self.view_class.form_class
            else:
                form_class = self.form_class
        form = form_class(data=data, files=files, initial=initial)
        form.is_valid()
        return form
        

class TestMIZAdminToolView(BaseTestView):
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
    
class TestFavoritenView(BaseTestView):
    
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
    
class TestMIZSessionWizardView(BaseTestView):
    
    view_class = MIZSessionWizardView
    
    def test_get_context_data(self):
        # what even is there to test?
        pass
    
#DBentry.bulk
class TestBulkAusgabe(BaseTestView, BaseFormViewMixin):
    
    view_class = BulkAusgabe
    path = reverse('bulk_ausgabe')
    
    @classmethod
    def setUpTestData(cls):
        super(TestBulkAusgabe, cls).setUpTestData()
        cls.mag = magazin.objects.create(magazin_name='Testmagazin')
        cls.zraum = lagerort.objects.create(pk=ZRAUM_ID, ort='Wayne')
        cls.dublette = lagerort.objects.create(pk=DUPLETTEN_ID, ort='Interessierts')
        cls.audio_lo = lagerort.objects.create(ort='Audio LO')
        g = geber.objects.create(name='TestGeber')
        cls.prov = provenienz.objects.create(geber=g, typ='Fund')
        
        # Create an instance that should be updated by the view
        cls.updated = ausgabe.objects.create(pk=111, magazin=cls.mag)
        cls.updated.ausgabe_jahr_set.create(jahr=2000)
        cls.updated.ausgabe_jahr_set.create(jahr=2001)
        cls.updated.ausgabe_num_set.create(num=1)
        
        # Create two identical objects to verify that the view simply does nothing if it cannot uniquely resolve an 
        # instance given by a form through its ['jahr', 'num', 'monat', 'lnum'] sets
        cls.multi1 = ausgabe.objects.create(pk=222, magazin=cls.mag)
        cls.multi1.ausgabe_jahr_set.create(jahr=2000)
        cls.multi1.ausgabe_jahr_set.create(jahr=2001)
        cls.multi1.ausgabe_num_set.create(num=5)
        cls.multi2 = ausgabe.objects.create(pk=333, magazin=cls.mag)
        cls.multi2.ausgabe_jahr_set.create(jahr=2000)
        cls.multi2.ausgabe_jahr_set.create(jahr=2001)
        cls.multi2.ausgabe_num_set.create(num=5)
    
    def setUp(self):
        super(TestBulkAusgabe, self).setUp()
        self.session = self.client.session
        self.session['old_form_data'] = {}
        self.session.save()
        self.valid_data = dict(
            magazin         = self.mag.pk, 
            jahrgang        = '11', 
            jahr            = '2000,2001', 
            num             = '1,2,3,4,4,5', 
            monat           = '', 
            lnum            = '', 
            audio           = True, 
            audio_lagerort  = self.audio_lo.pk, 
            lagerort        = '', 
            dublette        = '', 
            provenienz      = self.prov.pk, 
            info            = '', 
            status          = 'unb', 
            _debug          = False, 
        )
        
    def test_post_has_changed_message(self):
        # form.has_changed ( data != initial) :
        # => message 'Angaben haben sich geändert. Bitte kontrolliere diese in der Vorschau.')
        self.session['old_form_data'] = {'jahr':'2001'} #effectively changing form.initial
        self.session.save()
        response = self.client.post(self.path, data=self.valid_data)
        expected_message = 'Angaben haben sich geändert. Bitte kontrolliere diese in der Vorschau.'
        messages = [str(msg) for msg in get_messages(response.wsgi_request)]
        self.assertTrue(expected_message in messages)
        self.assertEqual(response.status_code, 200)
        
    def test_post_preview_in_POST(self):
        # _preview in request.POST => build_preview
        response = self.client.post(self.path, data=self.valid_data)
        self.assertTrue('preview_headers' in response.context)
        self.assertTrue('preview' in response.context)
        self.assertEqual(response.status_code, 200)
    
    def test_post_save_and_continue(self):
        # _continue in request.POST => save_data => redirect success_url
        data = self.valid_data.copy()
        data['_continue'] = True
        preview_response = self.client.post(self.path, data=data, follow=False) # get the 'preview' response
        response = self.client.post(self.path, data=data, follow=False) # get the '_continue' response
        self.assertTrue('_continue' in response.wsgi_request.POST)
        self.assertTrue('qs' in response.wsgi_request.session)
        self.assertEqual(response.status_code, 302) # 302 for redirect
        
    def test_post_save_and_addanother(self):
        # _addanother in request.POST => build_preview
        data = self.valid_data.copy()
        data['_addanother'] = True
        preview_response = self.client.post(self.path, data=data) # get the 'preview' response
        response = self.client.post(self.path, data=data) # get the '_continue' response
        messages = [str(msg) for msg in get_messages(response.wsgi_request)]
        self.assertTrue(any(msg.startswith('Ausgaben erstellt:') for msg in messages))
        self.assertTrue(any(msg.startswith('Dubletten hinzugefügt:') for msg in messages))
        self.assertTrue('preview_headers' in response.context)
        self.assertTrue('preview' in response.context)
        self.assertEqual(response.status_code, 200)
        
    def test_save_data_updated(self):
        form = self.get_form()
        request = self.post_request()
        self.assertFalse(self.updated.audio.exists())
        ids, created, updated = self.view(request).save_data(request, form)
        self.assertTrue(self.updated.audio.exists())
        
    def test_save_data_created(self):
        form = self.get_form()
        request = self.post_request()
        ids, created, updated = self.view(request).save_data(request, form)
        
        # Check the newly created instances
        self.assertEqual(len(created), 3)
        expected_num = 2
        for instance in created:
            self.assertEqual(instance.magazin.pk, self.mag.pk)
            self.assertEqual(instance.jahrgang, 11)
            self.assertEqual(list(instance.ausgabe_jahr_set.values_list('jahr', flat=True)), [2000, 2001])
            self.assertEqual(list(instance.ausgabe_num_set.values_list('num', flat=True)), [expected_num])
            expected_num+=1
        
        
    def test_next_initial_data(self):
        form = self.get_form()
        next_data = self.view().next_initial_data(form)
        self.assertEqual(next_data.get('jahrgang', 0), 12)
        self.assertEqual(next_data.get('jahr', ''), '2002, 2003')
        
    def test_instance_data(self):
        # nothing to test, it's all constants
        pass
        
    def build_preview(self):
        pass

#DBentry.ac.views
class BaseTestACView(BaseTestView):
    
    model = None
    create_field = None
    
    def view(self, request=None, args=None, kwargs=None, model = None, create_field = None, forwarded = None, q = None):
        self.view_class.model = model or self.model
        self.view_class.create_field = create_field or self.create_field
        self.view_class.forwarded = forwarded or {}
        self.view_class.q = q or ''
        return super(BaseTestACView, self).view(request, args, kwargs)
    
class TestACBase(BaseTestACView):
    
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
        
class TestACProv(BaseTestACView):
    
    view_class = ACProv
    path = reverse('acprov')
    model = provenienz
    
    def test_has_create_field(self):
        self.assertTrue(self.view().has_create_field())
        
    def test_create_object(self):
        obj = self.view().create_object('Beep')
        self.assertEqual(obj.geber.name, 'Beep')
        
class TestACAusgabe(BaseTestACView):
    
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
