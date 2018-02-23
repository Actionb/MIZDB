from .base import *
        
class TestACBase(ACViewTestMethodMixin, ACViewTestCase):
    
    view_class = ACBase
    path = reverse('acband')
    model = band
    create_field = 'band_name'
    test_data_count = 0

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = band.objects.create(band_name='Boop')
        cls.genre = genre.objects.create(genre='Testgenre')
        m2m_band_genre.objects.create(band=cls.obj1, genre=cls.genre)
        cls.musiker = musiker.objects.create(kuenstler_name='Meehh')
        m2m_band_musiker.objects.create(band=cls.obj1, musiker=cls.musiker)
        cls.obj2 = band.objects.create(band_name='aleboop')
        cls.obj3 = band.objects.create(band_name='notfound')
        cls.obj4 = band.objects.create(band_name='Boopband')
        
        cls.test_data = [cls.obj1, cls.obj2, cls.obj3, cls.obj4]
        
        super(TestACBase, cls).setUpTestData()
    
    def test_has_create_field(self):
        v = self.view()
        self.assertTrue(v.has_create_field())
        v.create_field = ''
        self.assertFalse(v.has_create_field())
        
    def test_has_add_permission(self):
        # Test largely covered by test_get_create_option_no_perms
        request = self.get_request(user=self.noperms_user)
        self.assertFalse(self.view().has_add_permission(request)) 
        
    def test_get_create_option_no_create_field(self):
        # No create option should be displayed if there is no create_field
        request = self.get_request()
        view = self.view(request)
        view.create_field = ''
        create_option = view.get_create_option(context={}, q='')
        self.assertEqual(create_option, [])
        
    def test_get_create_option_no_perms(self):
        # No create option should be displayed if the user has no add permissions
        request = self.get_request(user=self.noperms_user)
        create_option = self.view(request).get_create_option(context={}, q='Beep')
        self.assertEqual(create_option, [])
        
    def test_get_create_option_more_pages(self):
        # No create option should be displayed if there is more than one page to show
        request = self.get_request(user=self.noperms_user)
        page_obj = type('Dummy', (object, ), {'number':2})()
        create_option = self.view(request).get_create_option(context={'page_obj':page_obj}, q='Beep')
        self.assertEqual(create_option, [])
        
    def test_apply_q(self):
        # Test the ordering of exact_match_qs, startswith_qs and then contains_qs
        view = self.view(q='Boop')
        # obj1 is the only exact match
        # obj4 starts with q
        # obj2 contains q
        self.assertEqual(list(view.apply_q(self.queryset)), [self.obj1, self.obj4, self.obj2])
        
        # all but obj3 contain 'oop', standard ordering should apply  as there are neither exact nor startswith matches
        view.q = 'oop'
        self.assertEqual(list(view.apply_q(self.queryset)), [self.obj2, self.obj1, self.obj4])
        
        # only obj4 should appear
        view.q = 'Boopband'
        self.assertEqual(list(view.apply_q(self.queryset)), [self.obj4])
        
    def test_apply_q_favorites(self):
        fav = Favoriten.objects.create(user=self.super_user)
        fav.fav_genres.add(self.genre)
        first_genre = genre.objects.create(genre='A')
        request = self.get_request()
        view = self.view(request=request, model=genre)
        self.assertTrue(Favoriten.objects.filter(user=view.request.user).exists())
        # self.genre will show up twice in the result; once as part of favorites and then as the 'result' of the qs filtering
        self.assertEqual(list(view.apply_q(genre.objects.all())), [self.genre, first_genre, self.genre])
        
    def test_get_queryset_with_q(self):
        request = self.get_request()
        view = self.view(request)
        view.q = 'notfound'
        self.assertEqual(list(view.get_queryset()), [self.obj3])
        
    def test_get_queryset_forwarded(self):
        # fake forwarded attribute
        request = self.get_request()
        view = self.view(request)
        view.forwarded = {'genre':self.genre.pk, 'TROUBLES__musiker':self.musiker.pk}
        
        # get_queryset should filter out the problematic TROUBLES__musiker and '' forwards
        self.assertEqual(list(view.get_queryset()), [self.obj1])
        view.forwarded = {'':'ignore_me'}
        self.assertFalse(view.get_queryset().exists())
        
class TestACProv(ACViewTestMethodMixin, ACViewTestCase):
    
    view_class = ACProv
    path = reverse('acprov')
    model = provenienz
    
    def test_has_create_field(self):
        self.assertTrue(self.view().has_create_field())
       
    @tag('logging') 
    def test_create_object_no_log_entry(self):
        # no request set on view, no log entry should be created
        obj = self.view().create_object('Beep')
        self.assertEqual(obj.geber.name, 'Beep')
        with self.assertRaises(AssertionError):
            self.assertLoggedAddition(obj)
        
    @tag('logging')
    def test_create_object_with_log_entry(self):
        # request set on view, log entry should be created
        request = self.get_request()
        obj = self.view(request).create_object('Beep')
        self.assertLoggedAddition(obj)
        
@skip("reworked")
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
        

class TestACPerson(ACViewTestMethodMixin, ACViewTestCase):
    # ComputedNameModel
    model = person
    path = reverse('acperson')

class TestACAutor(ACViewTestMethodMixin, ACViewTestCase):
    # ComputedNameModel
    model = autor
    path = reverse('acautor')

class TestACMusiker(ACViewTestMethodMixin, ACViewTestCase):
    model = musiker
    path = reverse('acmusiker')

class TestACLand(ACViewTestMethodMixin, ACViewTestCase):
    model = land
    path = reverse('acland')

class TestACInstrument(ACViewTestMethodMixin, ACViewTestCase):
    model = instrument
    path = reverse('acinstrument')

class TestACSender(ACViewTestMethodMixin, ACViewTestCase):
    model = sender
    path = reverse('acsender')

class TestACSpielort(ACViewTestMethodMixin, ACViewTestCase):
    model = spielort
    path = reverse('acspielort')

class TestACVeranstaltung(ACViewTestMethodMixin, ACViewTestCase):
    model = veranstaltung
    path = reverse('acveranstaltung')
    
class TestACGenre(ACViewTestMethodMixin, ACViewTestCase):
        
    model = genre
    path = reverse('acgenre')
        
    def test_apply_q_favorites(self):
        request = self.get_request()
        view = self.view(request=request)
        
        result = view.apply_q(self.queryset)
        # If the user has no favorites, it should return the untouched queryset
        self.assertEqual(list(result), list(self.queryset))
        
        # Create a favorite for the user 
        fav = Favoriten.objects.create(user=request.user)
        fav.fav_genres.add(self.obj1)
        # Create an object that should be displayed as the first in the results following default ordering
        first_object_in_ordering = self.model.objects.create(genre='A')
        
        # self.obj1 will show up twice in the result; once as part of favorites and then as the 'result' of the qs filtering
        result = view.apply_q(self.model.objects.all())
        self.assertEqual(list(result), [self.obj1] + list(self.model.objects.all()))
        
class TestACSchlagwort(ACViewTestMethodMixin, ACViewTestCase):
        
    model = schlagwort
    path = reverse('acschlagwort')
        
    def test_apply_q_favorites(self):
        request = self.get_request()
        view = self.view(request=request)
        
        result = view.apply_q(self.queryset)
        # If the user has no favorites, it should return the untouched queryset
        self.assertEqual(list(result), list(self.queryset))
        
        # Create a favorite for the user 
        fav = Favoriten.objects.create(user=request.user)
        fav.fav_schl.add(self.obj1)
        # Create an object that should be displayed as the first in the results following default ordering
        first_object_in_ordering = self.model.objects.create(schlagwort='A')
        
        # self.obj1 will show up twice in the result; once as part of favorites and then as the 'result' of the qs filtering
        result = view.apply_q(self.model.objects.all())
        self.assertEqual(list(result), [self.obj1] + list(self.model.objects.all()))
    
class TestACPrototype(ACViewTestCase):
    
    view_class = ACPrototype
    model = band
    path = reverse('acproto')
    primary = 'band_name'
    alias = 'band_alias__alias'
    secondary = 'musiker__kuenstler_name'
    suffix = {'band_alias__alias':'Band-Alias', 'musiker__kuenstler_name':'Band-Mitglied'}
    
    @classmethod
    def setUpTestData(cls):
        cls.obj1 = band.objects.create(band_name='Test')
        
        cls.obj2 = band.objects.create(band_name='Something')
        cls.obj2.band_alias_set.create(alias='Test')
        
        cls.obj3 = band.objects.create(band_name='Different')
        m = musiker.objects.create(kuenstler_name='Test')
        band.musiker.through.objects.create(band=cls.obj3, musiker=m)
        
        
        cls.test_data = [cls.obj1, cls.obj2, cls.obj3]
        
        super().setUpTestData()
        
    def get_view(self, *args, **kwargs):
        view = super().view(*args, **kwargs)
        view.primary = self.primary
        view.alias = self.alias
        view.secondary = self.secondary
        view.suffix = self.suffix
        return view
        
    def setUp(self):
        super().setUp()
        self.queryset = self.queryset.values_list('pk', 'band_name')
        self.view = self.get_view()
        
        
    def test_exact_match_primary(self):
        expected = (self.obj1.pk, self.obj1.band_name)
        self.assertEqual(self.view.exact_match(self.queryset, 'Test')[0], expected)
        
    def test_exact_match_alias(self):
        expected = (self.obj2.pk, self.obj2.band_name + " (Band-Alias)")
        self.assertEqual(self.view.exact_match(self.queryset, 'Test')[1], expected)
        
    def test_exact_match_secondary(self):
        expected = (self.obj3.pk, self.obj3.band_name + " (Band-Mitglied)")
        self.assertEqual(self.view.exact_match(self.queryset, 'Test')[2], expected)
        
