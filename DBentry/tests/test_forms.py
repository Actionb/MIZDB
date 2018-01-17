from .base import *

from DBentry.forms import *
from DBentry.bulk.forms import *

class BaseTestForm(TestCase):
    
    form_class = None
    valid_data = {}
    
    def get_form(self, kwargs = {}):
        return self.form_class(**kwargs)
        
    def get_valid_form(self):
        form = self.form_class(data=self.valid_data)
        form.is_valid()
        return form
            
class BaseTestModelForm(BaseTestForm):
    
    model = None
    fields = None
    data_count = 1
    add_relations = False
    test_data = []
    
    @classmethod
    def setUpTestData(cls):
        cls.test_data = DataFactory().create_data(cls.model, count=cls.data_count, add_relations = cls.add_relations)
        for c, obj in enumerate(cls.test_data, 1):
            setattr(cls, 'obj'+str(c), obj)
    
    def get_form(self, kwargs={}):
        return forms.modelform_factory(self.model, form=self.form_class, fields=self.fields)(**kwargs)
        
class TestFormBase(BaseTestModelForm):
    
    form_class = FormBase
    model = land
    fields = ['land_name', 'code']
    
    @classmethod
    def setUpTestData(cls):
        cls.obj1 = land.objects.create(land_name='Deutschland', code='DE')
        
    def test_init(self):
        # initial in kwargs
        kwargs = {'initial' : {'land_name':'Dschland'}}
        form = self.get_form(kwargs=kwargs)
        self.assertEqual(form.initial.get('land_name'),'Dschland')
        
        # test populating initial with not quite correct field names
        
        # as field path
        kwargs = {'initial' : {'xyz__land_name':'Dschland'}}
        form = self.get_form(kwargs=kwargs)
        self.assertEqual(form.initial.get('land_name'),'Dschland')
        
        # as partial match
        kwargs = {'initial' : {'abcland_namexyz':'Dschland'}}
        form = self.get_form(kwargs=kwargs)
        self.assertEqual(form.initial.get('land_name'),'Dschland')

    def test_validate_unique(self):
        kwargs = {'instance':self.obj1, 'data' : dict(land_name=self.obj1.land_name, code=self.obj1.code)}
        form = self.get_form(kwargs=kwargs)
        self.assertTrue(form.is_valid())
        self.assertFalse(form.errors)
        
        # attempt to create a duplicate of a unique
        kwargs = {'data' : dict(land_name=self.obj1.land_name, code=self.obj1.code)}
        form = self.get_form(kwargs=kwargs)
        self.assertFalse(form.is_valid())
        self.assertTrue(form.errors)
        # validate_unique should now set the DELETE flag in cleaned_data
        form.validate_unique()
        self.assertEqual(form.cleaned_data.get('DELETE', False), True) 
        
class TestInLineAusgabeForm(BaseTestModelForm):
    
    form_class = InLineAusgabeForm
    model = ausgabe.audio.through
    fields = model.get_required_fields(as_string=True) #['magazin', 'ausgabe', 'audio']
    
    @classmethod
    def setUpTestData(cls):
        super(TestInLineAusgabeForm, cls).setUpTestData()
        cls.mag = cls.obj1.ausgabe.magazin # all objects should have the same magazin
        
    def test_init(self):
        # test if initial for ausgabe.magazin is set properly during init
        kwargs = {'instance':self.obj1}
        form = self.get_form(kwargs=kwargs)
        self.assertEqual(form.instance, self.obj1)
        self.assertEqual(form.initial.get('magazin'), self.mag)
        
class TestArtikelForm(BaseTestModelForm):
    
    form_class = InLineAusgabeForm
    model = ausgabe.audio.through
    fields = model.get_required_fields(as_string=True) #['ausgabe', 'schlagzeile', 'seite']
    
    @classmethod
    def setUpTestData(cls):
        super(TestArtikelForm, cls).setUpTestData()
        cls.mag = cls.obj1.ausgabe.magazin # all objects should have the same magazin
    
    def test_init(self):
        # test if initial for ausgabe.magazin is set properly during init
        kwargs = {'instance':self.obj1}
        form = self.get_form(kwargs=kwargs)
        self.assertEqual(form.instance, self.obj1)
        self.assertEqual(form.initial.get('magazin'), self.mag)

class TestMIZAdminForm(BaseTestForm):
    
    form_class = MIZAdminForm
    form_class.base_fields['some_int'] = forms.IntegerField()
    form_class.base_fields['wrap_me'] = forms.CharField(widget=autocomplete.ModelSelect2(url='acmagazin'))
    
    def test_init(self):
        form = self.get_form()
        # everything wrapped?
        from DBentry.ac.widgets import EasyWidgetWrapper
        form = self.get_form()
        self.assertIsInstance(self.form_class.base_fields['wrap_me'].widget, EasyWidgetWrapper)
        self.assertNotIsInstance(self.form_class.base_fields['some_int'].widget, EasyWidgetWrapper)
        
        # make sure RelatedObjectLookups was added to Medja.js
        self.assertTrue('admin/js/admin/RelatedObjectLookups.js' in form.Media.js)
        
    def test_iter(self):
        form = self.get_form()
        from django.contrib.admin.helpers import Fieldset 
        for fs in form:
            self.assertIsInstance(fs, Fieldset)
            
    def test_media_prop(self):
        # Make sure jquery loaded in the right order
        media = self.get_form().media
        extra = '' if settings.DEBUG else '.min' 
        self.assertTrue('admin/js/jquery.init.js' in media._js)
        self.assertTrue('admin/js/vendor/jquery/jquery%s.js' % extra in media._js)
        self.assertEqual(media._js.index('admin/js/vendor/jquery/jquery%s.js' % extra), 0)
        self.assertEqual(media._js.index('admin/js/jquery.init.js'), 1)
        
    def test_changed_data_prop(self):
        kwargs = dict(data=dict(some_int='10'), initial=dict(some_int='10'))
        form = self.get_form(kwargs)
        self.assertFalse(form.changed_data)
        
        kwargs = dict(data=dict(some_int='11'), initial=dict(some_int='10'))
        form = self.get_form(kwargs)
        self.assertTrue(form.changed_data)
        
class TestBulkForm(BaseTestForm):
    
    form_class = BulkForm
    form_class.model = ausgabe
    form_class.base_fields['some_fld'] = forms.CharField(required = False)
    form_class.base_fields['some_bulkfield'] = BulkField(required = False, label = 'num') 
    form_class.base_fields['req_fld'] = BulkJahrField(required = False)
    form_class.at_least_one_required = ['req_fld']
    
    def test_init(self):
        # Test init taking the given each_fields parameter
        kwargs = dict(each_fields=['some_fld'])
        form = self.get_form(kwargs)
        self.assertEqual(sorted(form.each_fields), ['req_fld', 'some_fld'])
        
        # See if the fieldsets were set up properly
        self.assertEqual(sorted(form.fieldsets[0][1]['fields']), ['some_bulkfield', 'some_fld']) # not in at_least_one_required
        self.assertEqual(sorted(form.fieldsets[1][1]['fields']), ['req_fld']) # at_least_one_required
        
    def test_has_changed(self):
        kwargs = dict(data={'req_fld':'2001'}, initial={'req_fld':'2000'})
        form = self.get_form(kwargs)
        self.assertTrue(form.has_changed())
        self.assertFalse(form._row_data) # _row_data should be empty if anything about the form data has changed
        
    def test_clean_errors(self):        
        # total_count != item_count => error message
        kwargs = dict(data={'some_bulkfield':'1,2', 'req_fld' : '2000'})
        form = self.get_form(kwargs)
        form.is_valid()
        form.total_count = 1 # clean() expects total_count to be zero at the beginning
        try:
            form.clean()
        except ValidationError as e:
            self.assertEqual(e.message[:16],'Ungleiche Anzahl')
            
        # not all fields in at_least_one_required have data => error message
        kwargs = dict(data={'some_bulkfield':'1,2'})
        form = self.get_form(kwargs)
        form.is_valid()
        try:
            form.clean()
        except ValidationError as e:
            self.assertEqual(e.message[:16],'Bitte mindestens')
            
    def test_clean(self):
        kwargs = dict(data={'some_bulkfield':'1,2', 'req_fld' : '2000'})
        form = self.get_form(kwargs)
        form.is_valid()
        # check if split_data was populated correctly
        self.assertTrue('some_bulkfield' in form.split_data)
        self.assertEqual(sorted(form.split_data.get('some_bulkfield')), ['1', '2'])
        self.assertTrue('req_fld' in form.split_data)
        self.assertEqual(sorted(form.split_data.get('req_fld')), ['2000'])
        
class TestBulkFormAusgabe(BaseTestForm):
    
    form_class = BulkFormAusgabe
    
    @classmethod
    def setUpTestData(cls):
        cls.zraum = lagerort.objects.create(pk=ZRAUM_ID, ort='Wayne')
        cls.dublette = lagerort.objects.create(pk=DUPLETTEN_ID, ort='Interessierts')
        cls.mag = magazin.objects.create(magazin_name='Testmagazin')
        
        cls.obj1 = ausgabe.objects.create(magazin=cls.mag)
        cls.obj1.ausgabe_jahr_set.create(jahr=2000)
        cls.obj1.ausgabe_num_set.create(num=2)
        
        cls.obj2 = ausgabe.objects.create(magazin=cls.mag)
        cls.obj2.ausgabe_jahr_set.create(jahr=2000)
        cls.obj2.ausgabe_num_set.create(num=3)
        cls.obj3 = ausgabe.objects.create(magazin=cls.mag)
        cls.obj3.ausgabe_jahr_set.create(jahr=2000)
        cls.obj3.ausgabe_num_set.create(num=3)
        
    def setUp(self):
        self.valid_data = dict(
            magazin         = self.mag.pk, 
            jahrgang        = None, 
            jahr            = '2000', 
            num             = '1,2,3,4,4', 
            monat           = '', 
            lnum            = '', 
            audio           = False, 
            audio_lagerort  = None, 
            lagerort        = None, 
            dublette        = None, 
            provenienz      = None, 
            info            = '', 
            status          = 'unb', 
        )
    
    def test_clean(self):
        # audio == True v audio_lagerort == False => 'Bitte einen Lagerort für die Musik Beilage angeben.'
        data = self.valid_data.copy()
        data['audio'] = True
        kwargs = dict(data=data)
        form = self.get_form(kwargs)
        form.is_valid()
        
    def test_clean_lagerort(self):
        # not self.cleaned_data['lagerort'] => set lagerort
        form = self.get_valid_form()
        self.assertTrue('lagerort' in form.cleaned_data)
        self.assertEqual(form.cleaned_data.get('lagerort', None), self.zraum)
        
    def test_dublette(self):
        # not self.cleaned_data['dublette'] => set dublette
        form = self.get_valid_form()
        self.assertTrue('dublette' in form.cleaned_data)
        self.assertEqual(form.cleaned_data.get('dublette', None), self.dublette)
        
    @skip('deprecated')
    def test_row_data_lagerort(self):
        form = self.get_valid_form()
        lo = form.row_data_lagerort(form.row_data[0])
        self.assertEqual(lo, self.zraum)
        
        lo = form.row_data_lagerort(form.row_data[1])
        self.assertEqual(lo, self.dublette)
            
        
    def test_lookup_instance(self):
        # row['num'] == 2 => qs.exists() else !qs.exists()
        form = self.get_valid_form()
        for row in form.row_data:
            qs = form.lookup_instance(row)
            if row['num'] == '2':
                # this row is the 'unique' instance we created in setUpTestData
                self.assertEqual(qs.count(), 1)
            else:
                self.assertNotEqual(qs.count(), 1)
        
    def test_row_data_prop(self):
        # row[fld_name] = item => item creation
        
        # lagerort/dublette/multiple instances
        form = self.get_valid_form()
        row_data = form.row_data
        self.assertEqual(len(row_data), 5)
        # The first row should represent a completely new ausgabe
        self.assertEqual(row_data[0].get('lagerort', None), self.zraum)
        
        # The second row should represent a dublette of obj1
        self.assertEqual(row_data[1].get('lagerort', None), self.dublette)
        self.assertEqual(row_data[1].get('instance', None), self.obj1)
        
        # The third row should be marked as 'multiple' (a queryset), since we have two ausgabe instances that are 'the same'
        self.assertTrue('multiples' in row_data[2])
        self.assertTrue(self.obj2 in row_data[2]['multiples'])
        self.assertTrue(self.obj3 in row_data[2]['multiples'])
        
        # The last two rows represent a case where one row is an exact 'dupe' of the other
        # first row of these two passes through
        self.assertEqual(row_data[3].get('lagerort', None), self.zraum) 
        # the second is marked as a dublette of the first 
        self.assertEqual(row_data[4].get('lagerort', None), self.dublette) 
        self.assertTrue('dupe_of' in row_data[4])
        self.assertEqual(row_data[3], row_data[4]['dupe_of'])
        
        
class TestDynamicChoiceForm(BaseTestForm):
    
    def test_init(self):
        pass
    
class TestDynamicChoiceFormSet(BaseTestForm):
    
    def test_get_form_kwargs(self):
        pass
    
