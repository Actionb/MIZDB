from ..base import *

from DBentry.bulk.forms import *
  

class TestBulkForm(FormTestCase):
    
    form_class = BulkForm
    dummy_attrs = {
            'some_fld' : forms.CharField(required = False), 
            'some_bulkfield' : BulkField(required = False, label = 'num') , 
            'req_fld' : BulkJahrField(required = False), 
            'another' : forms.CharField(required = False), 
            'model' : ausgabe, 
            'each_fields' : ['another', 'some_fld'], 
            'at_least_one_required' : ['req_fld', 'some_bulkfield'], 
            'field_order' : ['some_fld', 'some_bulkfield', 'req_fld', 'another'], 
        }
    dummy_bases = (BulkForm, )
       
    def test_init_sets_fieldsets(self):
        # Assert that the form's fieldsets are set up properly during initial
        form = self.get_dummy_form()
        
        # The 'each' fieldset
        self.assertEqual(form.fieldsets[0][1]['fields'], ['some_fld', 'another'])
        
        # The 'at_least_one_required' fieldset
        self.assertEqual(form.fieldsets[1][1]['fields'], ['some_bulkfield', 'req_fld'])
       
    def test_has_changed(self):
        # _row_data should be empty if anything about the form data has changed
        data = {'req_fld':'2001'}
        initial = {'req_fld':'2000'}
        form = self.get_dummy_form(data=data, initial=initial)
        form._row_data = [1] # put *something* into _row_data
        self.assertTrue(form.has_changed())
        self.assertEqual(len(form._row_data), 0) 
         
    def test_clean_errors_uneven_item_count(self):        
        # total_count != item_count => error message
        data = {'some_bulkfield':'1,2', 'req_fld' : '2000'}
        form = self.get_dummy_form(data=data)
        form.total_count = 1 # clean() expects total_count to be zero at the beginning
        form.is_valid()
        self.assertTrue(form.has_error('some_bulkfield'))
        
    def test_clean_populating_split_data(self):
        # check if split_data was populated correctly
        data ={ 'some_bulkfield':'1,2', 'req_fld' : '2000', 'some_fld':'4,5'}
        form = self.get_dummy_form(data=data)
        form.is_valid()
        self.assertTrue(hasattr(form, 'split_data'))
        self.assertTrue('some_bulkfield' in form.split_data)
        self.assertEqual(sorted(form.split_data.get('some_bulkfield')), ['1', '2'])
        self.assertTrue('req_fld' in form.split_data)
        self.assertEqual(sorted(form.split_data.get('req_fld')), ['2000'])
        self.assertFalse('some_fld' in form.split_data)
    
    @tag("bug")
    def test_clean_handles_field_validation_errors(self):
        # If a BulkField raises a ValidationError during its cleaning process, the field's value is removed from cleaned_data.
        # The form's clean method needs to be able to handle an expected, but missing, field in cleaned_data.
        data ={ 'some_bulkfield':'ABC', 'req_fld' : '2000A', 'some_fld':'4,5'}
        form = self.get_dummy_form(data=data)
        with self.assertNotRaises(KeyError):
            form.is_valid()
            
    def test_clean_handles_to_list_errors(self):
        # A BulkField's to_list method may throw an error, the form must not allow it to bubble up
        data = {'some_bulkfield':'1,2-4**3', 'req_fld' : '2000', 'some_fld':'4,5'}
        form = self.get_dummy_form(data=data)
        with self.assertNotRaises(Exception):
            form.is_valid()       
   
class TestBulkFormAusgabe(TestDataMixin, FormTestCase):
    
    form_class = BulkFormAusgabe
    model = ausgabe
    
    @classmethod
    def setUpTestData(cls):
        cls.mag = make(magazin, magazin_name='Testmagazin')
        cls.zraum = make(lagerort, ort='Bestand LO')
        cls.dublette = make(lagerort, ort='Dubletten LO')
        cls.audio_lo = make(lagerort)
        cls.prov = make(provenienz)
        cls.updated = make(ausgabe, magazin=cls.mag, ausgabe_jahr__jahr=[2000, 2001], ausgabe_num__num=1)
        cls.multi1, cls.multi2 = batch(ausgabe, 2, magazin=cls.mag, ausgabe_jahr__jahr=[2000, 2001], ausgabe_num__num=5)
        
        cls.test_data = [cls.updated, cls.multi1, cls.multi2]
        
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
            ausgabe_lagerort= self.zraum.pk,  
            dublette        = self.dublette.pk, 
            provenienz      = self.prov.pk, 
            beschreibung    = '', 
            status          = 'unb', 
            _debug          = False, 
        )
        
    def test_init_fieldsets(self):
        form = self.get_form()
        # Each field fieldset
        expected = ['magazin', 'jahrgang', 'jahr', 'status', 'beschreibung', 'bemerkungen', 'audio', 'audio_lagerort', 'ausgabe_lagerort', 'dublette', 'provenienz']
        self.assertEqual(form.fieldsets[0][1]['fields'], expected)
        
        # At least one required fieldset
        expected = ['num', 'monat', 'lnum']
        self.assertEqual(form.fieldsets[1][1]['fields'], expected)
        
    def test_clean_errors_audio_but_no_audio_lagerort(self):
        # audio == True & audio_lagerort == False => 'Bitte einen Lagerort für die Musik Beilage angeben.'
        data = self.valid_data.copy()
        del data['audio_lagerort']
        form = self.get_form(data=data)
        form.is_valid()
        self.assertTrue(form.has_error('audio_lagerort'))
        
    def test_clean_errors_uneven_item_count(self):        
        # total_count != item_count => error message
        data = self.valid_data.copy()
        data['monat'] = '1'
        form = self.get_form(data=data)
        form.is_valid()
        self.assertTrue(form.has_error('monat'))
        
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
        
    def test_lookup_instance_jahrgang(self):
        pass
        
    def test_row_data_prop(self):
        # verify that form.row_data contains the expected data           
        form = self.get_valid_form()
        
        row_template = dict(
            magazin         = self.mag, 
            jahrgang        = 11, 
            jahr            = ['2000','2001'], 
            audio           = True, 
            audio_lagerort  = self.audio_lo, 
            ausgabe_lagerort= self.zraum,  
            dublette        = self.dublette, 
            provenienz      = self.prov, 
            status          = 'unb', 
        )
        # valid_data: num             = '1,2,3,4,4,5', ==> 
        row_1 = row_template.copy()
        row_1.update({'num':'1', 'ausgabe_lagerort':self.dublette,  'instance':self.obj1}) # should add a dublette
        row_2 = row_template.copy()
        row_2.update({'num':'2'}) # new object
        row_3 = row_template.copy()
        row_3.update({'num':'3'}) # new object
        row_4 = row_template.copy()
        row_4.update({'num':'4', }) # new object
        row_5 = row_template.copy()
        row_5.update({'num':'4', 'ausgabe_lagerort':self.dublette, 'dupe_of':row_4}) # dupe of the previous row and should be marked as a dublette of the previous row
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
            ausgabe_lagerort= self.zraum,  
            dublette        = self.dublette, 
            provenienz      = self.prov, 
            status          = 'unb', 
        )
        # valid_data: num             = '1,2,3,4,4,5', ==> 
        row_1 = row_template.copy()
        row_1.update({'num':'1', 'ausgabe_lagerort':self.dublette,  'instance':self.obj1}) # should add a dublette
        row_2 = row_template.copy()
        row_2.update({'num':'2'}) # new object
        row_3 = row_template.copy()
        row_3.update({'num':'3'}) # new object
        row_4 = row_template.copy()
        row_4.update({'num':'4', }) # new object
        row_5 = row_template.copy()
        row_5.update({'num':'4', 'ausgabe_lagerort':self.dublette, 'dupe_of':row_4}) # dupe of the previous row and should be marked as a dublette of the previous row
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
    @tag("wip")
    def test_row_data_prop_homeless_fielddata_present(self):
        # Make sure a BulkField that does not belong to either each_fields or at_least_one_required is still evaluated for row_data
        #NOTE: since this is working, doesn't that imply we do not need at_least_one_required?
        #TODO: what if the homeless field is not a bulkfield? Would it then behave as if it were in each_fields?
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
        
        form_class = type('DummyForm', (self.form_class, ), {'homeless':BulkField(), 'another':forms.CharField()})
        data['another'] = '1-6'
        form = form_class(data=data)
        self.assertTrue(all(row.get('another')=='1-6' for row in form.row_data))
        
    @translation_override(language = None)
    def test_clean_handles_month_gt_12(self):
        data = self.valid_data.copy()
        data['monat'] = '13'
        data['num'] = ''
        form = self.get_form(data=data)
        with self.assertRaises(ValidationError) as cm:
            form.clean_monat()
        self.assertEqual(cm.exception.args[0], 'Monat-Werte müssen zwischen 1 und 12 liegen.')
        
