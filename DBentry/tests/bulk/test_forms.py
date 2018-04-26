from ..base import *

from DBentry.bulk.forms import *
      
class TestBulkForm(FormTestCase):
    
    form_class = BulkForm
    dummy_fields = {
            'some_fld' : forms.CharField(required = False), 
            'some_bulkfield' : BulkField(required = False, label = 'num') , 
            'req_fld' : BulkJahrField(required = False), 
            'another' : forms.CharField(required = False), 
        }
    
    def get_dummy_form(self, fields=None, **form_initkwargs):
        fields = fields or self.dummy_fields
        form_class = type('DummyForm', (self.form_class, ), fields.copy())
        form_class.model = ausgabe
        form_class.each_fields = ['another']
        form_class.at_least_one_required = ['req_fld']
        form_class.field_order = ['some_fld', 'some_bulkfield', 'req_fld', 'another']
        return form_class(**form_initkwargs)
    
    def test_init_combining_kwargs(self):
        form = self.get_dummy_form(at_least_one_required = ['some_bulkfield'])
        self.assertEqual(sorted(form.at_least_one_required), sorted(['req_fld', 'some_bulkfield']))
        
        form = self.get_dummy_form(each_fields = ['some_bulkfield']) # Little cheat here: usually BulkFields do not get added to each_fields
        self.assertEqual(sorted(form.each_fields), sorted(['another', 'some_bulkfield', 'some_fld']))
    
    def test_init_each_fields(self):
        # Test init adding any non-declared non-BulkFields to it and excluding fields declared in at_least_one_required
        form = self.get_dummy_form()
        self.assertEqual(sorted(form.each_fields), sorted(['another', 'some_fld']))
    
    def test_init_defining_each_fields_with_duplicate(self):
        # Test init taking the given each_fields parameter that contains a field name that is also present in at_least_one_required
        # req_fld should only show up in at_least_one_required
        form = self.get_dummy_form(each_fields=['req_fld'], at_least_one_required = ['req_fld'])
        self.assertFalse('req_fld' in form.each_fields)
        self.assertTrue('req_fld' in form.at_least_one_required)
        
    def test_init_fieldsets_each_fields(self):
        # See if the fieldsets were set up properly, including its order
        # each fields fieldset
        form = self.get_dummy_form(at_least_one_required = ['some_bulkfield'])
        fs = form.fieldsets[0][1]
        expected = ['some_fld', 'another']
        self.assertEqual(fs['fields'], expected)
        
    def test_init_fieldsets_at_least_one_required(self):
        # See if the fieldsets were set up properly, including its order
        # At least one required fieldset
        form = self.get_dummy_form(at_least_one_required = ['some_bulkfield'])
        fs = form.fieldsets[1][1]
        expected = ['some_bulkfield', 'req_fld']
        self.assertEqual(fs['fields'], expected)
        
    def test_init_fieldsets_homeless_fields(self):
        # some_bulkfield is not assigned to at_least_one_required and is not allowed in each_fields
        form = self.get_dummy_form()
        self.assertTrue('some_bulkfield' in form.fieldsets[2][1]['fields'])
        
    def test_has_changed(self):
        # _row_data should be empty if anything about the form data has changed
        data = {'req_fld':'2001'}
        initial = {'req_fld':'2000'}
        form = self.get_dummy_form(data=data, initial=initial)
        form._row_data = [1]
        self.assertTrue(form.has_changed())
        self.assertEqual(len(form._row_data), 0) 
        
    def test_clean_errors_uneven_item_count(self):        
        # total_count != item_count => error message
        data = {'some_bulkfield':'1,2', 'req_fld' : '2000'}
        form = self.get_dummy_form(data=data)
        form.is_valid()
        form.total_count = 1 # clean() expects total_count to be zero at the beginning
        with self.assertRaises(ValidationError) as e:
            form.clean()
        self.assertTrue(e.exception.message.startswith('Ungleiche Anzahl'))
        try:
            form.clean()
        except ValidationError as e:
            self.assertTrue(e.message.startswith('Ungleiche Anzahl'))

    def test_clean_errors_required_missing(self):   
        # not all fields in at_least_one_required have data => error message
        data = {'some_bulkfield':'1,2'}
        form = self.get_dummy_form(data=data)
        form.is_valid()
        with self.assertRaises(ValidationError) as e:
            form.clean()
        self.assertTrue(e.exception.message.startswith('Bitte mindestens'))
            
    def test_clean_populating_split_data(self):
        # check if split_data was populated correctly
        data ={ 'some_bulkfield':'1,2', 'req_fld' : '2000', 'some_fld':'4,5'}
        form = self.get_dummy_form(data=data)
        form.is_valid()
        self.assertTrue('some_bulkfield' in form.split_data)
        self.assertEqual(sorted(form.split_data.get('some_bulkfield')), ['1', '2'])
        self.assertTrue('req_fld' in form.split_data)
        self.assertEqual(sorted(form.split_data.get('req_fld')), ['2000'])
        self.assertFalse('some_fld' in form.split_data)
    
    @tag("bug")
    def test_clean_handles_field_validation_errors(self):
        # If a BulkField raises a ValidationError during the its cleaning process, the field's value is removed from cleaned_data.
        # The form's clean method needs to be able to handle an expected, but missing, field in cleaned_data.
        data ={ 'some_bulkfield':'ABC', 'req_fld' : '2000A', 'some_fld':'4,5'}
        form = self.get_dummy_form(data=data)
        with self.assertNotRaises(KeyError):
            form.is_valid()
        
        
class TestBulkFormAusgabe(TestDataMixin, FormTestCase):
    
    form_class = BulkFormAusgabe
    model = ausgabe
    
    @classmethod
    def setUpTestData(cls):
        cls.mag = magazin.objects.create(magazin_name='Testmagazin')
        cls.zraum = lagerort.objects.create(pk=ZRAUM_ID, ort='Bestand LO')
        cls.dublette = lagerort.objects.create(pk=DUPLETTEN_ID, ort='Dublette LO')
        cls.audio_lo = lagerort.objects.create(ort='Audio LO')
        g = geber.objects.create(name='TestGeber')
        cls.prov = provenienz.objects.create(geber=g, typ='Fund')
        
        cls.obj1 = ausgabe.objects.create(magazin=cls.mag)
        cls.obj1.ausgabe_jahr_set.create(jahr=2000)
        cls.obj1.ausgabe_jahr_set.create(jahr=2001)
        cls.obj1.ausgabe_num_set.create(num=1)
        
        # Create two identical objects for test_lookup_instance_multi_result
        cls.obj2 = ausgabe.objects.create(magazin=cls.mag)
        cls.obj2.ausgabe_jahr_set.create(jahr=2000)
        cls.obj2.ausgabe_jahr_set.create(jahr=2001)
        cls.obj2.ausgabe_num_set.create(num=5)
        cls.obj3 = ausgabe.objects.create(magazin=cls.mag)
        cls.obj3.ausgabe_jahr_set.create(jahr=2000)
        cls.obj3.ausgabe_jahr_set.create(jahr=2001)
        cls.obj3.ausgabe_num_set.create(num=5)
        
        cls.test_data = [cls.obj1, cls.obj2, cls.obj3]
        
        super().setUpTestData()

    def setUp(self):
        super().setUp()
        self.valid_data = dict(
            magazin         = self.mag.pk, 
            jahrgang        = '11', 
            jahr            = '2000,2001', 
            num             = '1,2,3,4,4,5', 
            monat           = '', 
            lnum            = '', 
            audio           = True, 
            audio_lagerort  = self.audio_lo.pk, 
            lagerort        = self.zraum.pk,  
            dublette        = self.dublette.pk, 
            provenienz      = self.prov.pk, 
            info            = '', 
            status          = 'unb', 
            _debug          = False, 
        )
        
    def test_init_each_fields(self):
        form = self.get_form()
        expected = sorted({'magazin', 'jahrgang', 'jahr', 'status', 'info', 'audio', 'audio_lagerort', 'lagerort', 'dublette', 'provenienz'})
        self.assertEqual(sorted(form.each_fields), expected)
        
    def test_init_at_least_one_required_fields(self):
        form = self.get_form()
        self.assertEqual(sorted(form.at_least_one_required),  sorted({'num', 'monat', 'lnum'}))
        
    def test_init_fieldsets(self):
        form = self.get_form()
        # Each field fieldset
        fs = form.fieldsets[0][1]
        expected = ['magazin', 'jahrgang', 'jahr', 'status', 'info', 'audio', 'audio_lagerort', 'lagerort', 'dublette', 'provenienz']
        self.assertEqual(fs['fields'], expected)
        
        # At least one required fieldset
        fs = form.fieldsets[1][1]
        expected = ['num', 'monat', 'lnum']
        self.assertEqual(fs['fields'], expected)
    
    def test_clean_errors_audio_but_no_audio_lagerort(self):
        # audio == True & audio_lagerort == False => 'Bitte einen Lagerort für die Musik Beilage angeben.'
        data = self.valid_data.copy()
        del data['audio_lagerort']
        form = self.get_form(data=data)
        # imitate full_clean()
        form.cleaned_data = {}
        form._clean_fields()
        with self.assertRaises(ValidationError) as e:
            form.clean()
        self.assertEqual(e.exception.args[0], 'Bitte einen Lagerort für die Musik Beilage angeben.')
        self.assertTrue('Bitte einen Lagerort für die Musik Beilage angeben.' in form.errors.get('__all__'))
        
    def test_clean_errors_uneven_item_count(self):        
        # total_count != item_count => error message
        data = self.valid_data.copy()
        data['monat'] = '1'
        form = self.get_form(data=data)
        form.is_valid()
        #form.total_count = 1 # clean() expects total_count to be zero at the beginning
        with self.assertRaises(ValidationError) as e:
            form.clean()
        self.assertTrue(e.exception.message.startswith('Ungleiche Anzahl'))

    def test_clean_errors_required_missing(self):   
        # not all fields in at_least_one_required have data => error message
        data = {}
        form = self.get_form(data=data)
        form.is_valid()
        with self.assertRaises(ValidationError) as e:
            form.clean()
        self.assertTrue(e.exception.message.startswith('Bitte mindestens'))
        
    def test_lookup_instance_no_result(self):
        # row['num'] == 2 => qs.exists() else !qs.exists()
        form = self.get_valid_form()
        row_data = {'num':'2', 'jahr':'2000', 'lnum':'312', 'monat':'12'}
        self.assertEqual(form.lookup_instance(row_data).count(), 0)
        
    def test_lookup_instance_one_result(self):
        # row['num'] == 2 => qs.exists() else !qs.exists()
        form = self.get_valid_form()
        row_data = {'num':'1', 'jahr':['2000','2001']}
        self.assertEqual(form.lookup_instance(row_data).count(), 1)
        
    def test_lookup_instance_multi_result(self):
        # row['num'] == 2 => qs.exists() else !qs.exists()
        form = self.get_valid_form()
        row_data = {'num':'5', 'jahr':['2000','2001']}
        self.assertEqual(form.lookup_instance(row_data).count(), 2)
        
    def test_row_data_prop(self):
        # verify that form.row_data contains the expected data           
        form = self.get_valid_form()
        
        row_template = dict(
            magazin         = self.mag, 
            jahrgang        = 11, 
            jahr            = ['2000','2001'], 
            audio           = True, 
            audio_lagerort  = self.audio_lo, 
            lagerort        = self.zraum,  
            dublette        = self.dublette, 
            provenienz      = self.prov, 
            status          = 'unb', 
        )
        # valid_data: num             = '1,2,3,4,4,5', ==> 
        row_1 = row_template.copy()
        row_1.update({'num':'1', 'lagerort':self.dublette,  'instance':self.obj1}) # should add a dublette
        row_2 = row_template.copy()
        row_2.update({'num':'2'}) # new object
        row_3 = row_template.copy()
        row_3.update({'num':'3'}) # new object
        row_4 = row_template.copy()
        row_4.update({'num':'4', }) # new object
        row_5 = row_template.copy()
        row_5.update({'num':'4', 'lagerort':self.dublette, 'dupe_of':row_4}) # dupe of the previous row and should be marked as a dublette of the previous row
        row_6 = row_template.copy()
        row_6.update({'num':'5', 'multiples':ausgabe.objects.filter(pk__in=[self.obj2.pk, self.obj3.pk])}) 
        expected = [row_1, row_2, row_3, row_4, row_5, row_6]
        
        self.assertEqual(len(form.row_data), len(expected))
        
        for c, row in enumerate(form.row_data):
            if c in [1, 2, 3]:
                # make sure row_2, _3, _4 do not have an instance assigned to them
                self.assertIsNone(row.get('instance', None))
            self.assertDictsEqual(row, expected[c]) 
            
    def test_row_data_prop_form_changed(self):
        # verify that form.row_data contains the expected data if the form has changed        
        initial = self.valid_data.copy()
        data = self.valid_data.copy()
        data['jahrgang'] = 12
        form = self.get_form(data=data, initial=initial)
        
        self.assertTrue(form.has_changed())
        self.assertFormValid(form)
        
        row_template = dict(
            magazin         = self.mag, 
            jahrgang        = 12, 
            jahr            = ['2000','2001'], 
            audio           = True, 
            audio_lagerort  = self.audio_lo, 
            lagerort        = self.zraum,  
            dublette        = self.dublette, 
            provenienz      = self.prov, 
            status          = 'unb', 
        )
        # valid_data: num             = '1,2,3,4,4,5', ==> 
        row_1 = row_template.copy()
        row_1.update({'num':'1', 'lagerort':self.dublette,  'instance':self.obj1}) # should add a dublette
        row_2 = row_template.copy()
        row_2.update({'num':'2'}) # new object
        row_3 = row_template.copy()
        row_3.update({'num':'3'}) # new object
        row_4 = row_template.copy()
        row_4.update({'num':'4', }) # new object
        row_5 = row_template.copy()
        row_5.update({'num':'4', 'lagerort':self.dublette, 'dupe_of':row_4}) # dupe of the previous row and should be marked as a dublette of the previous row
        row_6 = row_template.copy()
        row_6.update({'num':'5', 'multiples':ausgabe.objects.filter(pk__in=[self.obj2.pk, self.obj3.pk])}) 
        expected = [row_1, row_2, row_3, row_4, row_5, row_6]
        
        self.assertEqual(len(form.row_data), len(expected))
        
        for c, row in enumerate(form.row_data):
            if c in [1, 2, 3]:
                # make sure row_2, _3, _4 do not have an instance assigned to them
                self.assertIsNone(row.get('instance', None))
            self.assertDictsEqual(row, expected[c]) 
                
    def test_row_data_prop_invalid(self):
        # If the form is invalid, row_data should return empty
        form = self.get_form()
        self.assertEqual(form.row_data, [])        
        
    def test_row_data_prop_homeless_fielddata_present(self):
        # Make sure a BulkField that does not belong to either each_fields or at_least_one_required is still evaluated for row_data
        form_class = type('DummyForm', (self.form_class, ), {'homeless':BulkField()})
        data = self.valid_data.copy()
        data['homeless'] = '9,8,7,6,5,5'
        form = form_class(data=data)
        self.assertFormValid(form)
        self.assertTrue(all('homeless' in row for row in form.row_data))
        self.assertEqual(form.row_data[0].get('homeless'), '9')
        self.assertEqual(form.row_data[1].get('homeless'), '8')
        self.assertEqual(form.row_data[2].get('homeless'), '7')
        self.assertEqual(form.row_data[3].get('homeless'), '6')
        self.assertEqual(form.row_data[4].get('homeless'), '5')
        self.assertEqual(form.row_data[5].get('homeless'), '5')
        
