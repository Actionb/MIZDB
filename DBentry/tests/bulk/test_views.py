from ..base import *

from DBentry.bulk.views import *

class BulkAusgabeTestCase(TestDataMixin, ViewTestCase, CreateFormViewMixin, LoggingTestMixin):
    
    model = ausgabe
    path = reverse('bulk_ausgabe')
    
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
            ausgabe_lagerort= self.zraum.pk,  
            dublette        = self.dublette.pk, 
            provenienz      = self.prov.pk, 
            beschreibung    = '', 
            bemerkungen     = '', 
            status          = 'unb', 
            _debug          = False, 
        )

class TestBulkAusgabe(BulkAusgabeTestCase):
    
    view_class = BulkAusgabe
    
    def test_view_available(self):
        if hasattr(self, 'path') and self.path:
            response = self.client.get(self.path)
            self.assertEqual(response.status_code, 200)
            
    def test_view_forbidden(self):
        if hasattr(self, 'path') and self.path:
            self.client.force_login(self.noperms_user)
            response = self.client.get(self.path)
            self.assertTemplateUsed(response, 'admin/403.html')
    
    def test_post_has_changed_message(self):
        # form.has_changed ( data != initial) :
        response = self.client.post(self.path, data=self.valid_data)
        expected_message = 'Angaben haben sich geändert. Bitte kontrolliere diese in der Vorschau.'
        self.assertMessageSent(response.wsgi_request, expected_message)
        self.assertEqual(response.status_code, 200)
        
    def test_post_preview_in_POST(self):
        # _preview in request.POST => build_preview
        data=self.valid_data.copy()
        data['_preview'] = True
        response = self.client.post(self.path, data=data)
        self.assertTrue('preview_headers' in response.context)
        self.assertTrue('preview' in response.context)
        self.assertEqual(response.status_code, 200)
    
    def test_post_save_and_continue(self):
        # _continue in request.POST => save_data => redirect success_url
        data = self.valid_data.copy()
        data['_continue'] = True
        self.session['old_form_data'] = data.copy() # so the form 'has not changed'
        self.session.save()
        response = self.client.post(self.path, data=data, follow=False) # get the '_continue' response
        self.assertTrue('_continue' in response.wsgi_request.POST)
        self.assertEqual(response.status_code, 302) # 302 for redirect
        
    def test_post_save_and_addanother_preview(self):
        # _addanother in request.POST => the next form should also display the new preview
        data = self.valid_data.copy()
        data['_addanother'] = True
        self.session['old_form_data'] = data.copy() # so the form 'has not changed'
        self.session.save()
        response = self.client.post(self.path, data=data) # get the '_addanother' response
        self.assertMessageSent(response.wsgi_request, 'Ausgaben erstellt:')
        self.assertMessageSent(response.wsgi_request, 'Dubletten hinzugefügt:')
        self.assertTrue('preview_headers' in response.context)
        self.assertTrue('preview' in response.context)
        self.assertEqual(response.status_code, 200)
        
    def test_post_addanother_next_form(self):
        # request a new form filled with the valid data of the first form + incremented jahrgang/jahr
        data = self.valid_data.copy()
        data['_addanother'] = True
        preview_response = self.client.post(self.path, data=data) # get the 'preview' response
        response = self.client.post(self.path, data=preview_response.wsgi_request.POST) # get the '_addanother' response
        
        form_data = response.context.get('form').data.dict()
        self.assertEqual(form_data['jahrgang'],  12)
        self.assertEqual(form_data['jahr'],  '2002, 2003')
        
    def test_save_data(self):
        form = self.get_valid_form()
        request = self.post_request()
        view = self.get_view(request)
        
        # store the currently existing pks
        before_save_ids = list(self.queryset.values_list('pk', flat=True))
        self.assertEqual(len(before_save_ids), 3)
        self.assertEqual(before_save_ids, [self.updated.pk, self.multi1.pk, self.multi2.pk])
        
        ids_of_altered_objects, created, updated = view.save_data(form)
        
        # for num 1 and 5 the database already had objects, make sure they are still there
        for pk in before_save_ids:
            self.assertTrue(self.queryset.filter(pk=pk).exists())   
        
        # inspect the created objects
        after_save_ids = list(self.queryset.values_list('pk', flat=True))
        # in total we should now have 6 objects (3 old ones + 3 new ones)
        self.assertEqual(len(after_save_ids), 6)
        # the pks of any object that was created/updated are stored in ids_of_altered_objects
        # compare them (and our unaltered objects) with the after_save_ids
        self.assertEqual(sorted(ids_of_altered_objects + [self.multi1.pk, self.multi2.pk]), sorted(after_save_ids))

    @tag('logging')
    def test_save_data_updated(self):
        # check that the object called 'updated' has had an audio record added to it
        form = self.get_valid_form()
        request = self.post_request()
        
        # the data in question should not exist yet
        self.assertFalse(self.updated.audio.exists())
        
        ids, created, updated = self.get_view(request).save_data(form)
        self.updated.refresh_from_db()
        self.assertTrue(self.updated.audio.exists())
        self.assertIsNotNone(self.updated.jahrgang)
        self.assertLoggedChange(self.updated, fields = ['jahrgang', 'status'])
        
        # only 'updated' should be in the list 
        self.assertEqual(updated, [self.updated])
        # Assert that the update was logged properly
        a = self.updated.audio.first()
        m2m_instance = ausgabe.audio.through.objects.get(ausgabe=self.updated, audio=a)
        self.assertLoggedAddition(a)
        self.assertLoggedAddition(a, a.bestand_set.first())
        self.assertLoggedAddition(self.updated, m2m_instance)
        self.assertLoggedAddition(a, m2m_instance)
        
    @tag('logging')
    def test_save_data_created(self):
        # Check the newly created instances
        
        # store the currently existing pks
        before_save_ids = list(self.queryset.values_list('pk', flat=True))
        self.assertEqual(len(before_save_ids), 3)
        self.assertEqual(before_save_ids, [self.updated.pk, self.multi1.pk, self.multi2.pk])
        
        form = self.get_valid_form()
        request = self.post_request()
        ids, created, updated = self.get_view(request).save_data(form)
        
        # for the data num = '1,2,3,4,4,5' we expect to have created three new objects for num 2, 3 and 4. 
        self.assertEqual(len(created), 3)
        
        # None of our previously created objects should be contained in created
        self.assertFalse(any(o in created for o in [self.updated, self.multi1, self.multi2]))
        
        # per number only one object should now exist and it must be in created
        for n in [2, 3, 4]:
            obj_qs = self.queryset.exclude(pk__in=before_save_ids).filter(ausgabe_num__num=n)
            self.assertTrue(obj_qs.exists(), "object for num = {} was not created. \nqueryset: {}\ncreated: {}".format(n, self.queryset.all(), created))
            self.assertEqual(obj_qs.count(), 1)
            self.assertIn(obj_qs.first(), created)
        
        # check that the created objects have the right data
        expected_num = 2
        for instance in created:
            self.assertEqual(instance.magazin.pk, self.mag.pk)
            self.assertEqual(instance.jahrgang, 11)
            self.assertEqual(list(instance.ausgabe_jahr_set.values_list('jahr', flat=True)), [2000, 2001])
            self.assertEqual(list(instance.ausgabe_num_set.values_list('num', flat=True)), [expected_num])
            self.assertFalse(instance.ausgabe_lnum_set.exists())
            self.assertFalse(instance.ausgabe_monat_set.exists())
            
            self.assertEqual(instance.audio.count(), 1)
            self.assertEqual(instance.audio.first().bestand_set.count(), 1)
            self.assertEqual(instance.audio.first().bestand_set.first().lagerort, self.audio_lo)
            if expected_num == 4:
                # we have created two bestand objects for num == 4
                self.assertEqual(instance.bestand_set.count(), 2)
                b1,  b2 = instance.bestand_set.all().order_by('lagerort__ort') # sort alphabetically -> Bestand LO, Dubletten LO
                self.assertEqual(b1.lagerort, self.zraum)
                self.assertEqual(b1.provenienz, self.prov)
                self.assertEqual(b2.lagerort, self.dublette)
                self.assertEqual(b2.provenienz, self.prov)
            else:
                self.assertEqual(instance.bestand_set.count(), 1)
                self.assertEqual(instance.bestand_set.first().lagerort, self.zraum)
                self.assertEqual(instance.bestand_set.first().provenienz, self.prov)
            
            self.assertFalse(instance.beschreibung)
            self.assertEqual(instance.status, 'unb')
            
            expected_num+=1
        
        # Assert that the creation of the objects was logged properly
        for instance in created:
            self.assertLoggedAddition(instance)
            for j in instance.ausgabe_jahr_set.all():
                self.assertLoggedAddition(instance, j)
            for n in instance.ausgabe_num_set.all():
                self.assertLoggedAddition(instance, n)
            a = instance.audio.first()
            m2m = ausgabe.audio.through.objects.get(ausgabe=instance, audio=a)
            self.assertLoggedAddition(instance, m2m)
            self.assertLoggedAddition(a, m2m)
            self.assertLoggedAddition(a, a.bestand_set.first())
            for b in instance.bestand_set.all():
                self.assertLoggedAddition(instance, b)
        
    def test_next_initial_data(self):
        form = self.get_valid_form()
        next_data = self.get_view().next_initial_data(form)
        self.assertEqual(next_data.get('jahrgang', 0), 12)
        self.assertEqual(next_data.get('jahr', ''), '2002, 2003')
        
        data = self.valid_data.copy()
        data['jahr'] = ''
        form = self.get_form(data=data)
        form.is_valid()
        next_data = self.get_view().next_initial_data(form)
        self.assertEqual(next_data.get('jahrgang', 0), 12)
        self.assertFalse(next_data.get('jahr'))
    

class TestBulkAusgabeStory(BulkAusgabeTestCase):
    
    view_class = BulkAusgabe
    
    def test_story(self):
        # User requests the page for the first time
        first_visit_response = self.client.post(self.path)
        first_visit_request = first_visit_response.wsgi_request
        self.assertEqual(first_visit_response.status_code, 200)
        # No preview should be displayed yet
        self.assertFalse('preview_headers' in first_visit_response.context)
        self.assertFalse('preview' in first_visit_response.context)        
        
        # replicate the form
        first_visit_initial = first_visit_request.session.get('old_form_data', {})
        # first visist should mean no initial data
        self.assertFalse(first_visit_initial)
        first_visit_form = BulkAusgabe.form_class(first_visit_request.POST, initial=first_visit_initial)
        # likewise, form should not contain data
        self.assertFalse(first_visit_form.data)
        
        
        # User enters valid data for the form and presses preview
        first_preview_data = self.valid_data.copy()
        first_preview_data['_preview'] = True
        
        first_preview_response = self.client.post(self.path, data=first_preview_data) # get the response that adds the preview display
        first_preview_request = first_preview_response.wsgi_request
        self.assertEqual(first_preview_response.status_code, 200)
        self.assertTrue('preview_headers' in first_preview_response.context)
        self.assertTrue('preview' in first_preview_response.context)
    
        
        # old_form_data should now contain the data used to stimulate the preview response
        first_preview_initial = first_preview_request.session.get('old_form_data', {})
        self.assertDictsEqual(first_preview_initial, first_preview_data)
        first_preview_form = BulkAusgabe.form_class(first_preview_request.POST, initial=first_preview_initial)
        # but the form should obviously now contain the (valid) data
        self.assertTrue(first_preview_form.data)
        self.assertTrue(first_preview_form.is_valid())
        
        
        # User changes data without refreshing the preview, complain about it
        complain_data = self.valid_data.copy()
        complain_data['jahrgang'] = '12'
                
        complain_response = self.client.post(self.path, data=complain_data)
        complain_request = complain_response.wsgi_request
        self.assertEqual(complain_response.status_code, 200)
        expected_message = 'Angaben haben sich geändert. Bitte kontrolliere diese in der Vorschau.'
        self.assertMessageSent(complain_request, expected_message)
        
        # The view should contain the preview updated with the changes
        self.assertTrue('preview_headers' in complain_response.context)
        self.assertTrue('preview' in complain_response.context)
        for row in complain_response.context['preview']:
            self.assertEqual(str(row['jahrgang']), '12')
        
        # The user press add_another
        first_add_data = complain_request.POST.copy()
        first_add_data['_addanother'] = True
        
        first_add_response = self.client.post(self.path, data=first_add_data)
        first_add_request = first_add_response.wsgi_request
        self.assertEqual(first_add_response.status_code, 200)
        
        # The user should have gotten some messages about the operation
        self.assertMessageSent(first_add_request, "Ausgaben erstellt:")
        self.assertMessageSent(first_add_request, "Dubletten hinzugefügt:")
        
        # The user press add_another again with incremented data
        second_add_data = first_add_response.context['form'].data.copy() # next_initial_data
        second_add_data['_addanother'] = True
                
        second_add_response = self.client.post(self.path, data=second_add_data)
        second_add_request = second_add_response.wsgi_request
        self.assertEqual(second_add_response.status_code, 200)
        
        # The view should contain the preview updated with the changes
        self.assertTrue('preview_headers' in second_add_response.context)
        self.assertTrue('preview' in second_add_response.context)
        for row in second_add_response.context['preview']:
            self.assertEqual(str(row['jahrgang']), '14')
        
        # As every object should have been newly created, the user only gets one message
        self.assertMessageSent(second_add_request, "Ausgaben erstellt:")
        self.assertMessageNotSent(second_add_request, "Dubletten hinzugefügt:")
        
        # Let's assume the session data contain the values of the old form gets 'lost' -- maybe it expired because the user went to drink a coffee
        self.session['old_form_data'] = {}
        self.session.save()
        
        missing_old_data_data = second_add_response.context['form'].data.copy()
        missing_old_data_data['_addanother'] = True
        
        missing_old_data_response = self.client.post(self.path, data=missing_old_data_data)
        missing_old_data_request = missing_old_data_response.wsgi_request
        self.assertEqual(missing_old_data_response.status_code, 200)
        
        # The user should be prompted about changes and preview should be displayed
        expected_message = 'Angaben haben sich geändert. Bitte kontrolliere diese in der Vorschau.'
        self.assertMessageSent(missing_old_data_request, expected_message)
        
        # The view should contain the same preview as second_add_response
        self.assertTrue('preview_headers' in missing_old_data_response.context)
        self.assertTrue('preview' in missing_old_data_response.context)
        for row in missing_old_data_response.context['preview']:
            self.assertEqual(str(row['jahrgang']), '14')
            
        # The user puts in new data and presses preview
        continue_data = self.valid_data.copy()
        continue_data['num'] = ''
        # A saved monat record is required
        jan = make(monat, monat='Januar')
        continue_data['monat'] = [str(jan.pk)]
        continue_data['jahr'] = ['2018']
        continue_data['jahrgang'] = ''
        continue_data['_preview'] = True
        
        continue_preview_response = self.client.post(self.path, data=continue_data)
        continue_preview_request = continue_preview_response.wsgi_request
        self.assertEqual(continue_preview_response.status_code, 200)
        self.assertMessageNotSent(continue_preview_request, 'Angaben haben sich geändert. Bitte kontrolliere diese in der Vorschau.')
        self.assertTrue('preview_headers' in continue_preview_response.context)
        self.assertTrue('preview' in continue_preview_response.context)
        
        # The user presses _continue and leaves the view successfully
        del continue_data['_preview']
        continue_data['_continue'] = True
        continue_response = self.client.post(self.path, data=continue_data)
        
        self.assertEqual(continue_response.status_code, 302) # 302 for redirect
        self.assertTrue(continue_response.url.startswith(reverse("admin:DBentry_ausgabe_changelist") + '?id__in=')) 
        
