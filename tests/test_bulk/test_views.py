from django.test import tag
from django.urls import reverse, reverse_lazy

import dbentry.models as _models
from dbentry.bulk.views import BulkAusgabe
from dbentry.tests.mixins import CreateFormViewMixin, LoggingTestMixin, TestDataMixin
from tests.case import ViewTestCase
from tests.factory import batch, make


class TestBulkAusgabe(TestDataMixin, ViewTestCase, CreateFormViewMixin, LoggingTestMixin):
    model = _models.Ausgabe
    view_class = BulkAusgabe
    path = reverse_lazy('bulk_ausgabe')

    @classmethod
    def setUpTestData(cls):
        cls.mag = make(_models.Magazin, magazin_name='Testmagazin')
        cls.lo = make(_models.Lagerort, ort='Bestand LO')
        cls.dublette = make(_models.Lagerort, ort='Dubletten LO')
        cls.audio_lo = make(_models.Lagerort)
        cls.prov = make(_models.Provenienz)
        # noinspection PyUnresolvedReferences
        cls.updated = make(
            cls.model,
            magazin=cls.mag,
            ausgabejahr__jahr=[2000, 2001],
            ausgabenum__num=1
        )
        # noinspection PyUnresolvedReferences
        cls.multi1, cls.multi2 = batch(
            cls.model, 2,
            magazin=cls.mag,
            ausgabejahr__jahr=[2000, 2001],
            ausgabenum__num=5
        )
        # noinspection PyUnresolvedReferences
        cls.test_data = [cls.updated, cls.multi1, cls.multi2]
        super().setUpTestData()

    def setUp(self):
        super().setUp()
        self.session = self.client.session
        self.session['old_form_data'] = {}
        self.session.save()
        self.valid_data = {
            'magazin': self.mag.pk,
            'jahrgang': 11,
            'jahr': '2000,2001',
            'num': '1,2,3,4,4,5',
            'monat': '',
            'lnum': '',
            'audio': True,
            'audio_lagerort': self.audio_lo.pk,
            'ausgabe_lagerort': self.lo.pk,
            'dublette': self.dublette.pk,
            'provenienz': self.prov.pk,
            'beschreibung': '',
            'bemerkungen': '',
            'status': 'unb'
        }

    def test_view_available(self):
        response = self.get_response(self.path, user=self.super_user)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/bulk.html')

    def test_view_forbidden(self):
        response = self.get_response(self.path, user=self.noperms_user)
        self.assertEqual(response.status_code, 403)

    def test_post_has_changed_message(self):
        """
        Assert that a warning message is displayed should the changed form be
        posted without having requested a preview.
        """
        response = self.post_response(self.path, data=self.valid_data)
        self.assertEqual(response.status_code, 200)
        self.assertMessageSent(
            response.wsgi_request,
            'Angaben haben sich geändert. Bitte kontrolliere diese in der Vorschau.'
        )

    def test_post_preview_in_POST(self):
        """Assert that the preview is generated when requested."""
        data = self.valid_data.copy()
        data['_preview'] = True
        response = self.post_response(self.path, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('preview_headers' in response.context)
        self.assertTrue('preview' in response.context)

    def test_post_save_and_continue(self):
        """
        Assert that after a successful 'continue' POST request, the user is
        redirected to the changelist filtered to the newly created instances.
        """
        data = self.valid_data.copy()
        data['_continue'] = True
        # The form's initial data is retrieved from the session.
        # Initial and form data must be equal for the form to not 'have changed'.
        self.session['old_form_data'] = data.copy()
        self.session.save()
        # Use follow = False to get the redirect response.
        response = self.post_response(self.path, data=data, follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("admin/dbentry/ausgabe/?id__in=", response.url)

    def test_post_save_and_addanother_preview(self):
        """
        Assert that the response to a 'add_another' POST request includes a
        preview of the next batch of items.
        """
        data = self.valid_data.copy()
        data['_addanother'] = True
        self.session['old_form_data'] = data.copy()
        self.session.save()
        response = self.client.post(self.path, data=data)
        self.assertMessageSent(response.wsgi_request, 'Ausgaben erstellt:')
        self.assertMessageSent(response.wsgi_request, 'Dubletten hinzugefügt:')
        self.assertTrue('preview_headers' in response.context)
        self.assertTrue('preview' in response.context)
        self.assertEqual(response.status_code, 200)

    def test_post_addanother_next_form(self):
        """Assert that jahrgang/jahr are incremented when requesting the next form."""
        data = self.valid_data.copy()
        data['_addanother'] = True
        self.session['old_form_data'] = data.copy()
        self.session.save()
        response = self.client.post(self.path, data=data)
        form_data = response.context.get('form').data.dict()
        self.assertEqual(form_data['jahrgang'], 12)
        self.assertEqual(form_data['jahr'], '2002,2003')

    def test_save_data(self):
        """Check the number of objects saved to the database."""
        form = self.get_valid_form()
        request = self.post_request()
        view = self.get_view(request)

        # Store the currently existing pks and check that these pks
        # correspond to the pks of our 'special objects'.
        before_save_ids = sorted(list(self.queryset.values_list('pk', flat=True)))
        self.assertEqual(len(before_save_ids), 3)
        self.assertEqual(before_save_ids, [self.updated.pk, self.multi1.pk, self.multi2.pk])

        ids_of_altered_objects, created, updated = view.save_data(form)
        # The database already contained objects with nums 1 and 5.
        # Make sure they are still there:
        for pk in before_save_ids:
            with self.subTest():
                self.assertTrue(
                    self.queryset.filter(pk=pk).exists(),
                    msg="Test object was deleted unexpectedly."
                )

        # Inspect the created objects:
        after_save_ids = list(self.queryset.values_list('pk', flat=True))
        # We should now have 6 objects (3 old ones + 3 new ones) in total:
        self.assertEqual(len(after_save_ids), 6)
        # The pks of any object that was created or updated are stored in
        # ids_of_altered_objects. Compare them (and our unaltered objects)
        # with the ids currently in the database.
        self.assertEqual(
            sorted(ids_of_altered_objects + [self.multi1.pk, self.multi2.pk]),
            sorted(after_save_ids)
        )

    @tag('logging')
    def test_save_data_updated(self):
        """Check the updates made to already existing instances."""
        # The test's model instance 'updated' should have had an audio record
        # added to it. An update to the 'jahrgang' value is also expected.
        form = self.get_valid_form()
        request = self.post_request()
        # The related audio instance should not exist yet.
        self.assertFalse(self.updated.audio.exists())
        # Perform the update and check the related audio set again.
        ids, created, updated = self.get_view(request).save_data(form)
        self.updated.refresh_from_db()
        # The 'updated' instance should be the only instance marked as updated.
        self.assertEqual(updated, [self.updated])
        self.assertTrue(self.updated.audio.exists())

        # Assert that the update was logged properly.
        new_audio = self.updated.audio.first()
        change_message = {}
        added = [{"added": change_message}]
        # Check that the creation of new_audio was logged:
        self.assertLoggedAddition(new_audio, change_message=added)
        # Check that the creation of the Bestand for new_audio was logged:
        change_message['name'] = 'Bestand'
        change_message['object'] = str(new_audio.bestand_set.first())
        self.assertLoggedAddition(new_audio, change_message=added)
        # Check that new_audio being added to 'updated' was logged:
        change_message['name'] = 'Audio Material'
        change_message['object'] = str(new_audio)
        self.assertLoggedAddition(self.updated, change_message=added)
        # Check that 'updated' being added to new_audio was logged:
        change_message['name'] = 'Ausgabe'
        change_message['object'] = str(self.updated)
        self.assertLoggedAddition(new_audio, change_message=added)
        # Check that a value for 'jahrgang' was added and that the addition
        # was logged correctly.
        self.assertIsNotNone(self.updated.jahrgang)
        self.assertLoggedChange(
            self.updated,
            change_message=[{"changed": {'fields': ['Jahrgang']}}]
        )

    @tag('logging')
    def test_save_data_created(self):
        """Check the newly created instances."""
        # Store the currently existing pks.
        before_save_ids = list(self.queryset.values_list('pk', flat=True))
        self.assertEqual(len(before_save_ids), 3)
        self.assertEqual(
            sorted(before_save_ids),
            sorted([self.updated.pk, self.multi1.pk, self.multi2.pk])
        )

        form = self.get_valid_form()
        request = self.post_request()
        ids, created, updated = self.get_view(request).save_data(form)
        preexisting = [self.updated, self.multi1, self.multi2]
        # From the data with num = '1,2,3,4,4,5' we expect to have created three
        # new objects for num 2, 3 and 4.
        self.assertEqual(len(created), 3)
        for n in [2, 3, 4]:
            with self.subTest(num=n):
                qs = self.queryset.filter(ausgabenum__num=n)
                self.assertEqual(qs.count(), 1)
                self.assertIn(qs.first(), created)
                self.assertNotIn(
                    qs.first(), preexisting,
                    msg="Preexisting object found in the collection that"
                        " should only contain explicitly new instances."
                )

        # Check that the created objects have the expected values.
        expected_num = 2  # noqa
        change_message = {}
        added = [{"added": change_message}]
        for instance, expected_num in zip(created, [2, 3, 4]):
            with self.subTest(num=n):
                self.assertEqual(instance.magazin.pk, self.mag.pk)
                self.assertEqual(instance.jahrgang, 11)
                self.assertFalse(instance.beschreibung)
                self.assertEqual(instance.status, 'unb')
                jahre = instance.ausgabejahr_set.values_list('jahr', flat=True)
                self.assertEqual(list(jahre), [2000, 2001])
                nums = instance.ausgabenum_set.values_list('num', flat=True)
                self.assertEqual(list(nums), [expected_num])
                self.assertFalse(instance.ausgabelnum_set.exists())
                self.assertFalse(instance.ausgabemonat_set.exists())
                self.assertEqual(instance.audio.count(), 1)
                self.assertEqual(instance.audio.first().bestand_set.count(), 1)
                self.assertEqual(
                    instance.audio.first().bestand_set.first().lagerort,
                    self.audio_lo
                )
            if expected_num == 4:
                # We have created two bestand objects for num == 4.
                self.assertEqual(instance.bestand_set.count(), 2)
                # Sort the bestand instances alphabetically -> Bestand LO, Dubletten LO.
                b1, b2 = instance.bestand_set.all().order_by('lagerort__ort')
                self.assertEqual(b1.lagerort, self.lo)
                self.assertEqual(b1.provenienz, self.prov)
                self.assertEqual(b2.lagerort, self.dublette)
                self.assertEqual(b2.provenienz, self.prov)
            else:
                self.assertEqual(instance.bestand_set.count(), 1)
                self.assertEqual(
                    instance.bestand_set.first().lagerort, self.lo
                )
                self.assertEqual(
                    instance.bestand_set.first().provenienz, self.prov
                )
                # Assert that the creation of the objects was logged properly.
                self.assertLoggedAddition(instance)
                # Check the logs for Jahr:
                change_message['name'] = 'Jahr'
                for j in instance.ausgabejahr_set.all():
                    change_message['object'] = str(j)
                    self.assertLoggedAddition(instance, change_message=added)
                # Check the logs for Num:
                change_message['name'] = 'Nummer'
                for n in instance.ausgabenum_set.all():
                    change_message['object'] = str(n)
                    self.assertLoggedAddition(instance, change_message=added)
                # Check the log for the new audio instance.
                new_audio = instance.audio.first()
                self.assertLoggedAddition(new_audio)
                # Check that the creation of the Bestand for new_audio was logged:
                change_message['name'] = 'Bestand'
                change_message['object'] = str(new_audio.bestand_set.first())
                self.assertLoggedAddition(new_audio, change_message=added)
                # Check that new_audio being added to 'instance' was logged:
                change_message['name'] = 'Audio Material'
                change_message['object'] = str(new_audio)
                self.assertLoggedAddition(instance, change_message=added)
                # Check that 'instance' being added to new_audio was logged:
                change_message['name'] = 'Ausgabe'
                change_message['object'] = str(instance)
                self.assertLoggedAddition(new_audio, change_message=added)
                # Check the logs for Bestand:
                change_message['name'] = 'Bestand'
                for b in instance.bestand_set.all():
                    change_message['object'] = str(b)
                    self.assertLoggedAddition(instance, change_message=added)

    def test_next_initial_data_increments_jahr(self):
        """Assert that next_initial_data increments the values for 'jahr'."""
        form = self.view_class.form_class(data=self.valid_data)
        self.assertTrue(form.is_valid(), msg=form.errors)
        next_data = self.get_view().next_initial_data(form)
        self.assertEqual(next_data['jahrgang'], 12)
        self.assertEqual(next_data['jahr'], '2002,2003')

    def test_next_initial_data_increments_jahrgang(self):
        """Assert that next_initial_data increments the values for 'jahrgang'."""
        data = self.valid_data.copy()
        data['jahr'] = ''
        form = self.get_form(data=data)
        form.is_valid()
        next_data = self.get_view().next_initial_data(form)
        self.assertEqual(next_data.get('jahrgang', 0), 12)
        self.assertFalse(next_data.get('jahr'))

    def test_javascript(self):
        """Check that jquery and select2 are included and in the right order."""
        with self.settings(DEBUG=True):
            response = self.get_response(self.path)
            self.assertSelect2JS(response.context['form'].media._js)

    def test_story(self):
        preview_msg = 'Angaben haben sich geändert. Bitte kontrolliere diese in der Vorschau.'

        # User requests the page for the first time.
        first_visit_response = self.client.post(self.path)
        first_visit_request = first_visit_response.wsgi_request
        self.assertEqual(first_visit_response.status_code, 200)
        # No preview should be displayed yet:
        self.assertFalse('preview_headers' in first_visit_response.context)
        self.assertFalse('preview' in first_visit_response.context)
        # The session storage for 'old_form_data' should be empty:
        self.assertFalse(first_visit_request.session.get('old_form_data'))

        # User enters valid data for the form and presses preview.
        first_preview_data = self.valid_data.copy()
        first_preview_data['_preview'] = True
        first_preview_response = self.client.post(self.path, data=first_preview_data)
        self.assertEqual(first_preview_response.status_code, 200)
        self.assertTrue('preview_headers' in first_preview_response.context)
        self.assertTrue('preview' in first_preview_response.context)

        # 'old_form_data' should now contain the data used to stimulate the
        # preview response:
        first_preview_request = first_preview_response.wsgi_request
        # Call dict(x.items()) to flatten the values of the QueryDict.
        first_preview_initial = dict(
            first_preview_request.session.get('old_form_data', {}).items()
        )
        # Convert values from first_preview_data to string so that they match
        # the type of the values in first_preview_initial.
        self.assertEqual(
            first_preview_initial, {k: str(v) for k, v in first_preview_data.items()}
        )

        # User changes data without refreshing the preview, complain about it:
        complain_data = self.valid_data.copy()
        complain_data['jahrgang'] = 12
        complain_response = self.client.post(self.path, data=complain_data)
        self.assertEqual(complain_response.status_code, 200)
        complain_request = complain_response.wsgi_request
        self.assertMessageSent(complain_request, preview_msg)

        # The view should contain the preview updated with the changes:
        self.assertTrue('preview_headers' in complain_response.context)
        self.assertTrue('preview' in complain_response.context)
        for row in complain_response.context['preview']:
            self.assertEqual(str(row['jahrgang']), '12')

        # The user press 'add_another':
        first_add_data = complain_request.POST.copy()
        first_add_data['_addanother'] = True
        first_add_response = self.client.post(self.path, data=first_add_data)
        self.assertEqual(first_add_response.status_code, 200)

        # The user should have gotten some messages about the operation:
        first_add_request = first_add_response.wsgi_request
        self.assertMessageSent(first_add_request, "Ausgaben erstellt:")
        self.assertMessageSent(first_add_request, "Dubletten hinzugefügt:")

        # The user presses 'add_another' again with incremented data:
        # The form data of first_add_response is the data for this next step.
        second_add_data = first_add_response.context['form'].data.copy()
        second_add_data['_addanother'] = True
        second_add_response = self.client.post(self.path, data=second_add_data)
        second_add_request = second_add_response.wsgi_request
        self.assertEqual(second_add_response.status_code, 200)

        # The view should contain the preview updated with the changes
        self.assertTrue('preview_headers' in second_add_response.context)
        self.assertTrue('preview' in second_add_response.context)
        for row in second_add_response.context['preview']:
            self.assertEqual(str(row['jahrgang']), '14')

        # As every object should have been newly created,
        # the user only gets one message:
        self.assertMessageSent(second_add_request, "Ausgaben erstellt:")
        self.assertMessageNotSent(second_add_request, "Dubletten hinzugefügt:")

        # Let's assume the session data contain the values of the old form gets 'lost'
        # -- maybe it expired because the user went to drink a coffee.
        self.session['old_form_data'] = {}
        self.session.save()
        missing_old_data_data = second_add_response.context['form'].data.copy()
        missing_old_data_data['_addanother'] = True
        missing_old_data_response = self.client.post(self.path, data=missing_old_data_data)
        self.assertEqual(missing_old_data_response.status_code, 200)
        # The user should get a message warning about the form having changed:
        missing_old_data_request = missing_old_data_response.wsgi_request
        self.assertMessageSent(missing_old_data_request, preview_msg)

        # The view should contain the same preview as second_add_response
        self.assertTrue('preview_headers' in missing_old_data_response.context)
        self.assertTrue('preview' in missing_old_data_response.context)
        for row in missing_old_data_response.context['preview']:
            self.assertEqual(str(row['jahrgang']), '14')

        # The user inputs new data and presses preview:
        continue_data = self.valid_data.copy()
        continue_data['num'] = ''
        # A saved monat record is required:
        jan = make(_models.Monat, monat='Januar')
        continue_data['monat'] = [str(jan.pk)]
        continue_data['jahr'] = ['2018']
        continue_data['jahrgang'] = ''
        continue_data['_preview'] = True

        continue_preview_response = self.client.post(self.path, data=continue_data)
        continue_preview_request = continue_preview_response.wsgi_request
        self.assertEqual(continue_preview_response.status_code, 200)
        self.assertMessageNotSent(continue_preview_request, preview_msg)
        self.assertTrue('preview_headers' in continue_preview_response.context)
        self.assertTrue('preview' in continue_preview_response.context)

        # The user presses _continue and leaves the view successfully;
        # redirected back to the ausgabe changelist filtered to the set of
        # recently created instances: "?id="
        del continue_data['_preview']
        continue_data['_continue'] = True
        continue_response = self.client.post(self.path, data=continue_data)
        self.assertEqual(continue_response.status_code, 302)
        changelist_url = reverse("admin:dbentry_ausgabe_changelist")
        self.assertTrue(continue_response.url.startswith(changelist_url))
        self.assertIn('id', continue_response.url)
