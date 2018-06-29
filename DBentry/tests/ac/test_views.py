from .base import *

#TODO: a cached result list was returned although an item of that result list only CONTAINED the search term
# search term: 'Katalog', cached result list: ['Blablkatalog','Zeugs']
        
class TestACBase(ACViewTestMethodMixin, ACViewTestCase):
    
    view_class = ACBase
    model = band
    create_field = 'band_name'
    test_data_count = 0

    @classmethod
    def setUpTestData(cls):
        cls.genre = make(genre, genre='Testgenre')
        cls.obj1 = make(band, band_name='Boop', genre=cls.genre, musiker__extra=1)
        cls.obj2 = make(band, band_name='Aleboop')
        cls.obj3 = make(band, band_name='notfound')
        cls.obj4 = make(band, band_name='Boopband')
        
        cls.test_data = [cls.obj1, cls.obj2, cls.obj3, cls.obj4]
        
        super(TestACBase, cls).setUpTestData()
    
    def test_has_create_field(self):
        v = self.get_view()
        self.assertTrue(v.has_create_field())
        v.create_field = ''
        self.assertFalse(v.has_create_field())
        
    def test_has_add_permission(self):
        # Test largely covered by test_get_create_option_no_perms
        request = self.get_request(user=self.noperms_user)
        self.assertFalse(self.get_view().has_add_permission(request)) 
        
    def test_get_create_option_no_create_field(self):
        # No create option should be displayed if there is no create_field
        request = self.get_request()
        view = self.get_view(request)
        view.create_field = ''
        create_option = view.get_create_option(context={}, q='')
        self.assertEqual(create_option, [])
        
    def test_get_create_option_no_perms(self):
        # No create option should be displayed if the user has no add permissions
        request = self.get_request(user=self.noperms_user)
        create_option = self.get_view(request).get_create_option(context={}, q='Beep')
        self.assertEqual(create_option, [])
        
    def test_get_create_option_more_pages(self):
        # No create option should be displayed if there is more than one page to show
        request = self.get_request()
        view = self.get_view(request)
        paginator, page_obj, queryset, is_paginated = view.paginate_queryset(self.queryset, 1)
        create_option = view.get_create_option(context={'page_obj':page_obj}, q='Beep')
        self.assertEqual(create_option, [])
        
    def test_apply_q(self):
        # Test the ordering of exact_match_qs, startswith_qs and then contains_qs
        view = self.get_view(q='Boop')
        # obj1 is the only exact match
        # obj4 starts with q
        # obj2 contains q
        self.assertEqual(list(view.apply_q(self.queryset)), [self.obj1, self.obj4, self.obj2])
        
        # all but obj3 contain 'oop', standard ordering should apply as there are neither exact nor startswith matches
        view.q = 'oop'
        self.assertEqual(list(view.apply_q(self.queryset)), [self.obj2, self.obj1, self.obj4])

        # only obj4 should appear
        view.q = 'Boopband'
        self.assertEqual(list(view.apply_q(self.queryset)), [self.obj4])
        
    def test_get_queryset_with_q(self):
        request = self.get_request()
        view = self.get_view(request)
        view.q = 'notfound'
        self.assertEqual(list(view.get_queryset()), [self.obj3])
        
    def test_get_queryset_forwarded(self):
        # fake forwarded attribute
        request = self.get_request()
        view = self.get_view(request)
        view.forwarded = {'genre':self.genre.pk}
        
        # get_queryset should filter out the useless '' forward
        self.assertEqual(list(view.get_queryset()), [self.obj1])
        view.forwarded = {'':'ignore_me'}
        self.assertFalse(view.get_queryset().exists())
        
class TestACAusgabe(ACViewTestCase):
    
    model = ausgabe
    view_class = ACCapture

    
    @classmethod
    def setUpTestData(cls):
        cls.mag = make(magazin, magazin_name='Testmagazin')
        cls.obj_num = make(ausgabe, magazin=cls.mag, ausgabe_jahr__jahr=2020, ausgabe_num__num=10)
        cls.obj_lnum = make(ausgabe, magazin=cls.mag, ausgabe_jahr__jahr=2020, ausgabe_lnum__lnum=10)
        cls.obj_monat = make(ausgabe, magazin=cls.mag, ausgabe_jahr__jahr=2020, ausgabe_monat__monat__monat='Januar')
        cls.obj_sonder = make(ausgabe, magazin=cls.mag, sonderausgabe = True, beschreibung = 'Special Edition')
        cls.obj_jahrg = make(ausgabe, magazin=cls.mag, jahrgang=12, ausgabe_num__num=13)
        
        cls.test_data = [cls.obj_num, cls.obj_lnum, cls.obj_monat, cls.obj_sonder, cls.obj_jahrg]
        
        super().setUpTestData()
        
    def test_do_ordering(self):
        pass
        
    def test_apply_q_num(self):
        view = self.get_view(q=self.obj_num.__str__())
        expected = (self.obj_num.pk, force_text(self.obj_num))
        self.assertIn(expected, list(view.apply_q(self.queryset)))
        
        self.obj_num.ausgabe_num_set.create(num=11)
        self.obj_num.refresh_from_db()
        view = self.get_view(q=self.obj_num.__str__())
        expected = (self.obj_num.pk, force_text(self.obj_num))
        self.assertIn(expected, list(view.apply_q(self.queryset)))
        
    def test_apply_q_lnum(self):
        view = self.get_view(q=self.obj_lnum.__str__())
        #expected_qs = list(self.queryset.filter(pk=self.obj_lnum.pk))
        expected = (self.obj_lnum.pk, force_text(self.obj_lnum))
        self.assertIn(expected, list(view.apply_q(self.queryset)))
        
        self.obj_lnum.ausgabe_lnum_set.create(lnum=11)
        self.obj_lnum.refresh_from_db()
        view = self.get_view(q=self.obj_lnum.__str__())
        expected = (self.obj_lnum.pk, force_text(self.obj_lnum))
        self.assertIn(expected, list(view.apply_q(self.queryset)))
        
    def test_apply_q_monat(self):
        view = self.get_view(q=self.obj_monat.__str__())
        expected = (self.obj_monat.pk, force_text(self.obj_monat))
        self.assertIn(expected, list(view.apply_q(self.queryset)))
        
        self.obj_monat.ausgabe_monat_set.create(monat=make(monat, monat='Februar'))
        self.obj_monat.refresh_from_db()
        view = self.get_view(q=self.obj_monat.__str__())
        expected = (self.obj_monat.pk, force_text(self.obj_monat))
        self.assertIn(expected, list(view.apply_q(self.queryset)))
        
    def test_apply_q_sonderausgabe_forwarded(self):
        view = self.get_view(q=self.obj_sonder.__str__(), forwarded={'magazin':self.mag.pk})
        expected = (self.obj_sonder.pk, force_text(self.obj_sonder))
        self.assertIn(expected, list(view.apply_q(self.queryset)))
        
    def test_apply_q_sonderausgabe(self):
        view = self.get_view(q=self.obj_sonder.__str__())
        expected = (self.obj_sonder.pk, force_text(self.obj_sonder))
        self.assertIn(expected, list(view.apply_q(self.queryset)))
        
    def test_apply_q_jahrgang(self):
        view = self.get_view(q=self.obj_jahrg.__str__())
        expected = (self.obj_jahrg.pk, force_text(self.obj_jahrg))
        self.assertIn(expected, list(view.apply_q(self.queryset)))

        
class TestACProv(ACViewTestMethodMixin, ACViewTestCase):
    model = provenienz

class TestACPerson(ACViewTestMethodMixin, ACViewTestCase):
    model = person

class TestACAutor(ACViewTestMethodMixin, ACViewTestCase):
    model = autor

class TestACMusiker(ACViewTestMethodMixin, ACViewTestCase):
    model = musiker

class TestACLand(ACViewTestMethodMixin, ACViewTestCase):
    model = land

class TestACInstrument(ACViewTestMethodMixin, ACViewTestCase):
    model = instrument

class TestACSender(ACViewTestMethodMixin, ACViewTestCase):
    model = sender

class TestACSpielort(ACViewTestMethodMixin, ACViewTestCase):
    model = spielort

class TestACVeranstaltung(ACViewTestMethodMixin, ACViewTestCase):
    model = veranstaltung
    
class TestACGenre(ACViewTestMethodMixin, ACViewTestCase):
        
    model = genre
        
    def test_apply_q_favorites(self):
        request = self.get_request()
        view = self.get_view(request=request)
        
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
        
    def test_apply_q_favorites(self):
        request = self.get_request()
        view = self.get_view(request=request)
        
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
