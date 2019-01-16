from .base import *

from DBentry.ac.creator import Creator
        
class TestACBase(ACViewTestMethodMixin, ACViewTestCase):
    
    view_class = ACBase
    model = band
    create_field = 'band_name'
    alias_accessor_name = 'band_alias_set'

    @classmethod
    def setUpTestData(cls):
        cls.genre = make(genre, genre='Testgenre')
        cls.obj1 = make(band, band_name='Boop', genre=cls.genre, musiker__extra=1, band_alias__alias = 'Voltaire')
        cls.obj2 = make(band, band_name='Aleboop', band_alias__alias = 'Nietsche')
        cls.obj3 = make(band, band_name='notfound', band_alias__alias = 'Descartes')
        cls.obj4 = make(band, band_name='Boopband', band_alias__alias = 'Kant')
        
        cls.test_data = [cls.obj1, cls.obj2, cls.obj3, cls.obj4]
        
        super(TestACBase, cls).setUpTestData()
    
    def test_has_create_field(self):
        v = self.get_view()
        self.assertTrue(v.has_create_field())
        v.create_field = ''
        self.assertFalse(v.has_create_field())
        
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
        expected = [
            (self.obj1.pk, self.obj1.__str__()), 
            (self.obj4.pk, self.obj4.__str__()), 
            (self.obj2.pk, self.obj2.__str__())
        ]
        self.assertEqual(list(view.apply_q(self.queryset)), expected)
        
        # all but obj3 contain 'oop', standard ordering should apply as there are neither exact nor startswith matches
        view.q = 'oop'
        expected = [
            (self.obj2.pk, self.obj2.__str__()), 
            (self.obj1.pk, self.obj1.__str__()), 
            (self.obj4.pk, self.obj4.__str__())
        ]
        self.assertEqual(list(view.apply_q(self.queryset)), expected)

        # only obj4 should appear
        view.q = 'Boopband'
        self.assertEqual(list(view.apply_q(self.queryset)), [(self.obj4.pk, self.obj4.__str__())])
        
    def test_get_queryset_with_q(self):
        request = self.get_request()
        view = self.get_view(request)
        view.q = 'notfound'
        self.assertEqual(list(view.get_queryset()), [(self.obj3.pk, self.obj3.__str__())])
        
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
    
    def test_dispatch_sets_model(self):
        # dispatch should set the model attribute from the url caught parameter 'model_name' if the view instance does not have one
        view = self.get_view()
        view.model = None
        try:
            view.dispatch(model_name = 'ausgabe')
        except:
            # view.dispatch will run fine until it calls super() without a request positional argument
            # the model attribute is set before that
            pass
        self.assertEqual(view.model._meta.model_name, 'ausgabe')
        
    def test_dispatch_sets_create_field(self):
        # Assert that dispatch can set the create field attribute from its kwargs.
        view = self.get_view()
        view.create_field = None
        try:
            view.dispatch(create_field = 'this aint no field')
        except:
            # view.dispatch will run fine until it calls super() without a request positional argument
            # the model attribute is set before that
            pass
        self.assertEqual(view.create_field, 'this aint no field')
        
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
        # Assert that a creator instance with the right model is created during dispatch()
        view = self.get_view()
        try:
            view.dispatch()
        except:
            # view.dispatch will run fine until it calls super() without a request positional argument
            # the creator attribute is set before that
            pass
        self.assertIsInstance(view.creator, Creator)
        self.assertEqual(view.creator.model, self.model)
        
    def test_createable(self):
        # Assert that createable returns True if:
        # - a new object can be created from the given parameters
        # - no objects already present in the database fit the given parameters
        
        request = self.get_request()
        view = self.get_view(request)
        view.creator = self.creator
        self.assertTrue(view.createable('Alice Testman (AT)'))
        make(autor, person__vorname = 'Alice', person__nachname = 'Testman', kuerzel = 'AT')
        self.assertFalse(view.createable('Alice Testman (AT)'))
        
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
        
        # get_creation_info cannot return an empty list, but get_create_option checks for it so...
        view.get_creation_info = mockv([])
        create_option = view.get_create_option(context = {}, q = 'Alice Testman (AT)') 
        self.assertEqual(len(create_option), 1)
        
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
            expected['text'] = 'Vorname: Alice'
            self.assertEqual(create_info[1], expected)
            expected = default.copy()
            expected['text'] = 'Nachname: Testman'
            self.assertEqual(create_info[2], expected)
            expected = default.copy()
            expected['text'] = 'Kürzel: AT'
            self.assertEqual(create_info[3], expected)
            
            # Test the correct handling of nested dicts
            sub = OrderedDict([
                ('text1', 'Beginning of nest'), 
                ('nested1', OrderedDict([
                    ('text2', 'Middle of nest'), 
                    ('nested2', OrderedDict([
                        ('text3', 'End of nest')
                        ]))
                    ]))
                ])
            mocked_creator.create = mockv(sub)
            create_info = view.get_creation_info('Alice Testman (AT)', creator = mocked_creator)
            self.assertEqual(create_info[0], default)
            expected = default.copy()
            expected['text'] = 'text1: Beginning of nest'
            self.assertEqual(create_info[1], expected)
            expected = default.copy()
            expected['text'] = 'text2: Middle of nest'
            self.assertEqual(create_info[2], expected)
            expected = default.copy()
            expected['text'] = 'text3: End of nest'
            self.assertEqual(create_info[3], expected)
            
        
        create_info = view.get_creation_info('Alice Testman (AT)', creator = self.creator)
            
        self.assertEqual(len(create_info), 4) # also asserts that the empty 'None' dictionary items were removed
        self.assertEqual(create_info[0], default)
        expected = default.copy()
        expected['text'] = 'Vorname: Alice'
        self.assertEqual(create_info[1], expected)
        expected = default.copy()
        expected['text'] = 'Nachname: Testman'
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
        expected_error_msg = 'Missing creator object or "create_field"'
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
        cls.obj_datum = make(ausgabe, magazin=cls.mag, e_datum = '1986-08-18')
        
        cls.test_data = [cls.obj_num, cls.obj_lnum, cls.obj_monat, cls.obj_sonder, cls.obj_jahrg]
        
        super().setUpTestData()
        
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
        
    def test_apply_q_datum(self):
        view = self.get_view(q=self.obj_datum.__str__())
        expected = (self.obj_datum.pk, force_text(self.obj_datum))
        self.assertIn(expected, view.apply_q(self.queryset))

        
class TestACProv(ACViewTestMethodMixin, ACViewTestCase):
    model = provenienz
    has_alias = False
    test_data_count = 1

class TestACPerson(ACViewTestMethodMixin, ACViewTestCase):
    model = person
    has_alias = False
    raw_data = [{'beschreibung':'Klingt komisch, ist aber so', 'bemerkungen':'Abschalten!'}]

class TestACAutor(ACViewTestMethodMixin, ACViewTestCase):
    model = autor
    raw_data = [{'beschreibung':'ABC'}, {'beschreibung':'DEF'}, {'beschreibung':'GHI'}] # beschreibung is a search_field and needs some data
    has_alias = False

class TestACMusiker(ACViewTestMethodMixin, ACViewTestCase):
    model = musiker
    alias_accessor_name = 'musiker_alias_set'
    raw_data = [{'musiker_alias__alias':'John', 'person__nachname':'James', 'beschreibung':'Description'}]

class TestACLand(ACViewTestMethodMixin, ACViewTestCase):
    model = land
    raw_data = [{'land_alias__alias':'Dschland'}]
    alias_accessor_name = 'land_alias_set'

class TestACInstrument(ACViewTestMethodMixin, ACViewTestCase):
    model = instrument
    raw_data = [
        {'instrument_alias__alias' : 'Klavier'},  
        {'instrument_alias__alias' : 'Laute Tröte'}, 
        {'instrument_alias__alias' : 'Hau Drauf'}, 
    ]
    alias_accessor_name = 'instrument_alias_set'

class TestACSender(ACViewTestMethodMixin, ACViewTestCase):
    model = sender
    alias_accessor_name = 'sender_alias_set'
    raw_data = [{'sender_alias__alias':'AliasSender'}]

class TestACSpielort(ACViewTestMethodMixin, ACViewTestCase):
    model = spielort
    alias_accessor_name = 'spielort_alias_set'
    raw_data = [{'spielort_alias__alias':'AliasSpielort'}]

class TestACVeranstaltung(ACViewTestMethodMixin, ACViewTestCase):
    model = veranstaltung
    alias_accessor_name = 'veranstaltung_alias_set'
    raw_data = [{'veranstaltung_alias__alias':'AliasVeranstaltung'}]
    
class TestACBuchband(ACViewTestCase):
    model = buch
    view_class = ACBuchband
    
    @classmethod
    def setUpTestData(cls):
        cls.obj1 = make(buch, titel = 'DerBuchband', is_buchband = True)
        cls.obj2 = make(buch, titel = 'DasBuch', buchband = cls.obj1)
        cls.obj3 = make(buch, titel = 'Buch')
        
        cls.test_data = [cls.obj1, cls.obj2, cls.obj3]
        
        super().setUpTestData()
        
    def test_gets_queryset_only_returns_buchband(self):
        # Assert that apply_q can only return buch instances that are a buchband
        view = self.get_view(q='Buch')
        result = view.get_queryset()
        self.assertEqual(len(result), 1)
        self.assertIn((self.obj1.pk, self.obj1.__str__()), result)
        
        self.obj1.qs().update(is_buchband=False)
        self.assertFalse(view.get_queryset())
        
class TestACGenre(ACViewTestMethodMixin, ACViewTestCase):
        
    model = genre
    alias_accessor_name = 'genre_alias_set'
    raw_data = [{'genre_alias__alias':'Beep', 'sub_genres__extra':1, 'ober__genre':'Obergenre'}]
        
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
        
        # self.obj1 will show up twice in an unfiltered result; once as part of favorites and then as part of the qs
        result = view.apply_q(self.model.objects.all())
        self.assertEqual(list(result), [self.obj1] + list(self.model.objects.all()))
        
class TestACSchlagwort(ACViewTestMethodMixin, ACViewTestCase):
        
    model = schlagwort
    alias_accessor_name = 'schlagwort_alias_set'
    raw_data = [{'unterbegriffe__extra': 1, 'ober__schlagwort': 'Oberbegriff', 'schlagwort_alias__alias':'AliasSchlagwort'}]
        
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
        
        # self.obj1 will show up twice in an unfiltered result; once as part of favorites and then as part of the qs
        result = view.apply_q(self.model.objects.all())
        self.assertEqual(list(result), [self.obj1] + list(self.model.objects.all()))
