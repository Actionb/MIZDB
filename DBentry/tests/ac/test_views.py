from .base import *
from django.db.models.query import QuerySet
from DBentry.ac.creator import Creator
        
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
        self.assertEqual(list(view.get_queryset()), [self.obj1])
        
        # get_queryset should filter out useless empty forward values and return an empty qs instead
        view.forwarded = {'':'ignore_me'}
        self.assertFalse(view.get_queryset().exists())
        view.forwarded = {'ignore_me_too':''}
        self.assertFalse(view.get_queryset().exists())
        
class TestACCapture(ViewTestCase):
    
    view_class = ACCapture
    
    def test_dispatch_sets_model(self):
        # dispatch should set the model attribute from the url caught parameter 'model_name' if the view instance does not have one
        view = self.get_view()
        view.model = None
        try:
            view.dispatch(model_name = 'ausgabe')
        except:
            pass
        self.assertEqual(view.model, ausgabe)
        
    def test_get_result_value(self):
        # result is a list
        view = self.get_view()
        self.assertEqual(view.get_result_value(['value', 'label']), 'value')
        
        # result is a model instance
        instance = make(genre)
        self.assertEqual(view.get_result_value(instance), str(instance.pk))
        
    def test_get_result_label(self):
        # result is a list
        view = self.get_view()
        self.assertEqual(view.get_result_label(['value', 'label']), 'label')
        
        # result is a model instance
        instance = make(genre, genre='All this testing')
        self.assertEqual(view.get_result_label(instance), 'All this testing')
        
class TestACCreateable(ACViewTestCase):
    
    model = autor
    view_class = ACCreateable
    
    def setUp(self):
        super().setUp()
        self.creator = Creator(autor)
    
    def test_dispatch_sets_creator(self):
        view = self.get_view()
        try:
            view.dispatch()
        except:
            pass
        self.assertIsInstance(view.creator, Creator)
    
    @translation_override(language = None)
    def test_get_create_option(self):
        # Assert that get_create_option appends a non-empty 'create_info' dict to the default create option list
        # IF q is createable
        request = self.get_request()
        view = self.get_view(request)
        view.creator = self.creator
        self.assertTrue(hasattr(view, 'get_creation_info'))
        view.get_creation_info = mockv([{'id': None, 'create_id': True, 'text': 'Test123'}])
        
        create_option = view.get_create_option(context = {}, q = 'Alice Testman (AT)') 
        self.assertEqual(len(create_option), 2, msg = ", ".join(str(d) for d in create_option))
        self.assertIn('Test123', [d['text'] for d in create_option])
        
        view.createable = mockv(False)
        self.assertFalse(view.get_create_option(context = {}, q = 'Nope'))

    @translation_override(language = None)
    def test_get_creation_info(self):
        default = {'id':None, 'create_id':True, 'text':'...mit folgenden Daten:'}
        sub = OrderedDict([
            ('Person', OrderedDict(
                [('Vorname','Alice'), ('Nachname','Testman'), ('None', None), ('instance','Nope'), 
            ])), 
            ('Kürzel','AT'), 
            ('None', None), 
            ('instance', 'Nope'), 
        ])
        
        view = self.get_view()
        with patch('DBentry.ac.creator.Creator', autospec = True, spec_set = True) as mocked_creator:
            view.creator = mocked_creator
            mocked_creator.create = mockv(sub)
            create_info = view.get_creation_info('Alice Testman (AT)', creator = mocked_creator)
                
            self.assertEqual(len(create_info), 4) # also asserts that the empty 'None' dictionary items were removed
            self.assertEqual(create_info[0], default)
            expected = default.copy()
            expected['text'] = ' '*4 + 'Vorname: Alice'
            self.assertEqual(create_info[1], expected)
            expected = default.copy()
            expected['text'] = ' '*4 + 'Nachname: Testman'
            self.assertEqual(create_info[2], expected)
            expected = default.copy()
            expected['text'] = 'Kürzel: AT'
            self.assertEqual(create_info[3], expected)
            
            #TODO: NYI: Test the correct handling of nested dicts
            sub['Person']['nested_dicts'] = dict(nested1=dict(nested2=dict(nested3='End of nest')))
            mocked_creator.create = mockv(sub)
            create_info = view.get_creation_info('Alice Testman (AT)', creator = mocked_creator)
            
        
        create_info = view.get_creation_info('Alice Testman (AT)', creator = self.creator)
            
        self.assertEqual(len(create_info), 4) # also asserts that the empty 'None' dictionary items were removed
        self.assertEqual(create_info[0], default)
        expected = default.copy()
        expected['text'] = ' '*4 + 'Vorname: Alice'
        self.assertEqual(create_info[1], expected)
        expected = default.copy()
        expected['text'] = ' '*4 + 'Nachname: Testman'
        self.assertEqual(create_info[2], expected)
        expected = default.copy()
        expected['text'] = 'Kürzel: AT'
        self.assertEqual(create_info[3], expected)
            
    def test_create_object(self):
        obj1 = make(autor, person__vorname = 'Alice', person__nachname = 'Testman', kuerzel = 'AT')
        view = self.get_view()
        view.creator = self.creator
        
        # a new record
        obj1 = view.create_object('Alice Testman (AT)')
        self.assertEqual(obj1.person.vorname, 'Alice')
        self.assertEqual(obj1.person.nachname, 'Testman')
        self.assertEqual(obj1.kuerzel, 'AT')
        self.assertIsNotNone(obj1.pk)
        self.assertIsNotNone(obj1.person.pk)
        
        # if the view has a create field, the create field should be used instead
        view.create_field = 'kuerzel'
        created = view.create_object('BT')
        self.assertEqual(created.kuerzel, 'BT')
        self.assertIsNone(created.person)
        
        # fetch an existing record
        view.creator.create = mockv({'instance':obj1})
        view.create_field = None
        created = view.create_object(str(obj1))
        self.assertEqual(created.person.vorname, 'Alice')
        self.assertEqual(created.person.nachname, 'Testman')
        self.assertEqual(created.kuerzel, 'AT')
        self.assertEqual(created, obj1)
        self.assertEqual(created.person, obj1.person)
        
    def test_post(self):
        # Assert that post raises an AttributeError exception if self.creator is unset and self.create_field is unset
        expected_error_msg = 'Missing "create_field"'
        request = self.post_request(data = {'text': 'Alice Testman (AT)'})
        view = self.get_view()
        
        # both creator and create_field are None
        view.creator = None
        view.create_field = None
        with self.assertRaises(AttributeError) as cm:
            view.post(request)
        self.assertEqual(cm.exception.args[0], expected_error_msg)
        
        # create_field is None
        view.creator = self.creator
        with self.assertNotRaises(AttributeError) as cm:
            view.post(request)
        
        # creator is None
        view.creator = None
        view.create_field = 'kuerzel'
        with self.assertNotRaises(AttributeError) as cm:
            view.post(request)
        
        # both are set
        view.creator = self.creator
        with self.assertNotRaises(AttributeError) as cm:
            view.post(request)
        self.assertTrue(autor.objects.filter(person__vorname = 'Alice', person__nachname = 'Testman', kuerzel = 'AT').exists())
            
class TestACAusgabe2(ACViewTestCase):
    #NOTE: should all the queryset filtering be done with _name__icontains=q?
    model = ausgabe
    path = 'acausgabe'
    view_class = ACAusgabe
    
    @classmethod
    def setUpTestData(cls):
        possible_pks = list(range(1, 1001))
        def get_random_pk():
            # 'randomize' the pk values so we cannot rely on them for ordering
            return possible_pks.pop(random.randrange(0, len(possible_pks)-1))
        
        cls.mags = cls.mag_num, cls.mag_lnum, cls.mag_monat, cls.mag_jg = batch(magazin, 4)
        cls.nums = []
        cls.lnums = []
        cls.monate = []
        cls.jgs = []
        cls.mag = make(magazin)
        
        for jg, year in enumerate(range(1999, 2005)):
            for i in range(12):
                cls.nums.append(make(ausgabe, 
                    pk = get_random_pk(), magazin = cls.mag, ausgabe_num__num = i, ausgabe_jahr__jahr = year
                ))
                cls.lnums.append(make(ausgabe, 
                    pk = get_random_pk(), magazin = cls.mag, ausgabe_lnum__lnum = i, ausgabe_jahr__jahr = year
                ))
                cls.monate.append(make(ausgabe, 
                    pk = get_random_pk(), magazin = cls.mag, ausgabe_monat__monat__ordinal = i, ausgabe_jahr__jahr = year
                ))
                cls.jgs.append(make(ausgabe, 
                    pk = get_random_pk(), magazin = cls.mag, ausgabe_num__num = i, jahrgang = jg
                ))
        cls.all = cls.nums + cls.lnums + cls.monate + cls.jgs
        super().setUpTestData()
        
    def setUp(self):
        # We do not need the 'qs_objX' attribute TestDataMixin.setUp would create for us.
        # By not having an empty test_data attribute, TestDataMixin will skip that part, reducing db hits.
        for o in self.all:
            o.refresh_from_db()
        super().setUp
    
    def get_search_results(self, view, q):
        view.q = q
        result = view.get_queryset()
        if isinstance(result, QuerySet):
            return result.values_list('_name', flat = True)
        return [tpl[1] for tpl in result]
        
    def filter(self, _list, qs):
        filtered = qs.values_list('ausgabe_id', flat = True)
        return [o._name for o in _list if o.pk in filtered]
        
    def assertOrderingEqual(self, a, b):
        # Might be faster..?
        if len(a) != len(b):
            raise AssertionError()
        for i in range(len(a)-1):
            if a[i] != b[i]:
                raise AssertionError()
                
    def test_ordering_mixed(self):
        # If no criteria (num, lnum, monat) dominates over the others, the general order should be:
        # lnum, monat, num
        view = self.get_view(request = self.get_request())
        qs = ausgabe_jahr.objects.filter(jahr=2001)
        expected = self.filter(self.lnums, qs) + self.filter(self.monate, qs) + self.filter(self.nums, qs)
        self.assertEqual(self.get_search_results(view, '2001'), expected)
        
        # num dominant
        
        # lnum dominant
        
        # monat dominant
        
        # if jahr and jahrgang are present in the search results:
        # pick the one that is most dominant or neither if both are equally presented
        
        # jahr dominant: jahrgang ordering removed
        # --> any records with jahrgang and no jahr will be at the top
        filtered = ausgabe_lnum.objects.filter(lnum=11).values_list('ausgabe_id', flat = True)
        filtered += ausgabe_num.objects.filter(num=11).values_list('ausgabe_id', flat = True)
        
        expected = [o._name for o in chain(cls.jgs, cls.nums, cls.lnums) if o.pk in filtered]
        self.assertEqual(self.get_search_results(view, '11'), expected)
        
        # jahrgang dominant: jahr ordering removed
        # --> any records with jahr and no jahrgang will be at the top
        view.queryset = ausgabe.objects.filter(pk__in=chain(self.nums[3:], self.jgs))
        expected = self.filter(self.nums[3:]+ self.jgs, ausgabe_num.objects.filter(num=11))
        self.assertEqual(self.get_search_results(view, '11'), expected)
        
        # both equal, order should depend on -id
        view.queryset = ausgabe.objects.filter(pk__in=chain(self.nums, self.jgs))
        filtered = ausgabe_num.objects.filter(num=11).values_list('ausgabe_id', flat = True)
        expected = [o._name for o in sorted(
            [o for o in chain(self.jgs, self.nums) if o in filtered], 
            key = lambda o: o.pk
        )]
        self.assertEqual(self.get_search_results(view, '11'), expected)
        
    def test_ordering_num(self):
        view = self.get_view(request = self.get_request())
        view.queryset = ausgabe.objects.filter(pk__in=[o.pk for o in self.nums])
        
        expected = [o._name for o in self.nums]
        self.assertEqual(self.get_search_results(view, ''), expected)
        
        expected = self.filter(self.nums, view.queryset.filter(ausgabe_jahr__jahr=2001))
        self.assertEqual(self.get_search_results(view, '2001'), expected)
        
        expected = self.filter(self.nums, view.queryset.filter(ausgabe_num__num=11)) 
        self.assertEqual(self.get_search_results(view, '11'), expected)
        
    def test_ordering_lnum(self):
        view = self.get_view(request = self.get_request())
        view.queryset = ausgabe.objects.filter(pk__in=[o.pk for o in self.lnums])
        
        expected = [o._name for o in self.lnums]
        self.assertEqual(self.get_search_results(view, ''), expected)
        
        expected = self.filter(self.lnums, view.queryset.filter(ausgabe_jahr__jahr=2001))
        self.assertEqual(self.get_search_results(view, '2001'), expected)
        
        expected = self.filter(self.lnums, view.queryset.filter(ausgabe_lnum__lnum=11))
        self.assertEqual(self.get_search_results(view, '11'), expected)
        
    def test_ordering_monate(self):
        view = self.get_view(request = self.get_request())
        view.queryset = ausgabe.objects.filter(pk__in=[o.pk for o in self.monate])
        
        expected = [o._name for o in self.monate]
        self.assertEqual(self.get_search_results(view, ''), expected)
        
        expected = self.filter(self.monate, view.queryset.filter(ausgabe_jahr__jahr=2001))
        self.assertEqual(self.get_search_results(view, '2001'), expected)
        
        expected = self.filter(self.monate, view.queryset.filter(ausgabe_monat__monat__abk='Nov'))
        self.assertEqual(self.get_search_results(view, 'Nov'), expected)
        
    def test_ordering_jg(self):
        view = self.get_view(request = self.get_request())
        view.queryset = ausgabe.objects.filter(pk__in=[o.pk for o in self.jgs])
        
        expected = [o._name for o in self.jgs]
        self.assertEqual(self.get_search_results(view, ''), expected)
        
        expected = self.filter(o.self.nums, view.queryset.filter(jahrgang=2))
        self.assertEqual(self.get_search_results(view, 'Jg. 2'), expected)
        
        expected = self.filter(self.nums, view.queryset.filter(ausgabe_num__num=11))
        self.assertEqual(self.get_search_results(view, '11'), expected)
        
    def test_x(self):
        with self.assertNumQueries(1):
            filter(self.nums, ausgabe_jahr.objects.filter(jahr=2001))
        
class TestACAusgabe(ACViewTestCase):
    
    model = ausgabe
    path = 'acausgabe'
    view_class = ACAusgabe

    
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
        self.assertIn(expected, view.apply_q(self.queryset))
        
        # search for 10/11
        self.obj_num.ausgabe_num_set.create(num=11)
        self.obj_num.refresh_from_db()
        view = self.get_view(q=self.obj_num.__str__())
        expected = (self.obj_num.pk, force_text(self.obj_num))
        self.assertIn(expected, view.apply_q(self.queryset))
        
    def test_apply_q_lnum(self):
        view = self.get_view(q=self.obj_lnum.__str__())
        expected = (self.obj_lnum.pk, force_text(self.obj_lnum))
        self.assertIn(expected, view.apply_q(self.queryset))
        
        # search for 10/11
        self.obj_lnum.ausgabe_lnum_set.create(lnum=11)
        self.obj_lnum.refresh_from_db()
        view = self.get_view(q=self.obj_lnum.__str__())
        expected = (self.obj_lnum.pk, force_text(self.obj_lnum))
        self.assertIn(expected, view.apply_q(self.queryset))
        
    def test_apply_q_monat(self):
        view = self.get_view(q=self.obj_monat.__str__())
        expected = (self.obj_monat.pk, force_text(self.obj_monat))
        self.assertIn(expected, view.apply_q(self.queryset))
        
        # search for Jan/Feb
        self.obj_monat.ausgabe_monat_set.create(monat=make(monat, monat='Februar'))
        self.obj_monat.refresh_from_db()
        view = self.get_view(q=self.obj_monat.__str__())
        expected = (self.obj_monat.pk, force_text(self.obj_monat))
        self.assertIn(expected, view.apply_q(self.queryset))

    def test_apply_q_sonderausgabe(self):
        view = self.get_view(q=self.obj_sonder.__str__())
        expected = (self.obj_sonder.pk, force_text(self.obj_sonder))
        self.assertIn(expected, view.apply_q(self.queryset))
        
        view = self.get_view(q=self.obj_sonder.__str__(), forwarded={'magazin':self.mag.pk})
        expected = (self.obj_sonder.pk, force_text(self.obj_sonder))
        self.assertIn(expected, view.apply_q(self.queryset))
        
    def test_apply_q_jahrgang(self):
        view = self.get_view(q=self.obj_jahrg.__str__())
        expected = (self.obj_jahrg.pk, force_text(self.obj_jahrg))
        self.assertIn(expected, view.apply_q(self.queryset))

        
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
        make(genre, genre='A')
        
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
        make(schlagwort, schlagwort='A')
        
        # self.obj1 will show up twice in the result; once as part of favorites and then as the 'result' of the qs filtering
        result = view.apply_q(self.model.objects.all())
        self.assertEqual(list(result), [self.obj1] + list(self.model.objects.all()))
