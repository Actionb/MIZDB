from unittest import mock
from unittest.mock import patch

from django.contrib.auth import get_permission_codename
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core import checks
from django.test import RequestFactory, TestCase, override_settings

from dbentry.admin.base import AutocompleteMixin
from dbentry.admin.changelist import MIZChangeList
from tests.case import AdminTestCase
from tests.model_factory import make
from tests.test_admin.admin import AudioAdmin, BandAdmin, admin_site, PersonAdmin
from tests.test_admin.models import Audio, Band, Bestand, Person, Veranstaltung


class TestAutocompleteMixin(TestCase):
    class DummyModelField:
        name = "dummy"
        related_model = "anything"

    def test_formfield_for_foreignkey(self):
        """
        Assert that formfield_for_foreignkey calls make_widget with tabular=True
        if the field's name is in the inline's 'tabular_autocomplete' list.
        """
        with patch("dbentry.admin.base.super"):
            with patch("dbentry.admin.base.make_widget") as make_mock:
                inline = AutocompleteMixin()
                inline.tabular_autocomplete = ["dummy"]
                inline.formfield_for_foreignkey(db_field=self.DummyModelField(), request=None)  # noqa

                make_mock.assert_called()
                args, kwargs = make_mock.call_args
                self.assertIn("tabular", kwargs)
                self.assertTrue(kwargs["tabular"])

    def test_formfield_for_foreignkey_no_tabular(self):
        """
        Assert that formfield_for_foreignkey calls make_widget with tabular=False
        if the field's name isn't present in the 'tabular_autocomplete' list.
        """
        with patch("dbentry.admin.base.super"):
            with patch("dbentry.admin.base.make_widget") as make_mock:
                inline = AutocompleteMixin()
                inline.tabular_autocomplete = []
                inline.formfield_for_foreignkey(db_field=self.DummyModelField(), request=None)  # noqa

                make_mock.assert_called()
                _args, kwargs = make_mock.call_args
                self.assertIn("tabular", kwargs)
                self.assertFalse(kwargs["tabular"])

    def test_formfield_for_foreignkey_no_override(self):
        """
        Assert that formfield_for_foreignkey does not call make_widget if a
        widget was passed in.
        """
        with patch("dbentry.admin.base.super"):
            with patch("dbentry.admin.base.make_widget") as make_mock:
                inline = AutocompleteMixin()
                inline.tabular_autocomplete = []
                inline.formfield_for_foreignkey(db_field=self.DummyModelField(), request=None, widget=object)  # noqa
                make_mock.assert_not_called()


@override_settings(ROOT_URLCONF="tests.test_admin.urls")
class MIZModelAdminTest(AdminTestCase):
    admin_site = admin_site
    model_admin_class = AudioAdmin
    model = Audio

    @classmethod
    def setUpTestData(cls):
        cls.obj = make(cls.model, musiker__extra=1, band__extra=1, veranstaltung__extra=1)
        super().setUpTestData()

    def test_check_fieldset_fields(self):
        """Assert that _check_fieldset_fields finds invalid field declarations."""
        with patch.object(self.model_admin, "fieldsets"):
            # Should ignore an empty fieldsets attribute or fieldsets without a
            # 'fields' item:
            self.model_admin.fieldsets = None
            self.assertFalse(self.model_admin._check_fieldset_fields())
            self.model_admin.fieldsets = [("name", {"no_fields": "item"})]
            self.assertFalse(self.model_admin._check_fieldset_fields())

            # 'titel' is a valid field:
            self.model_admin.fieldsets = [(None, {"fields": ["titel"]})]
            self.assertFalse(self.model_admin._check_fieldset_fields())

            # Now use a field that doesn't exist:
            self.model_admin.fieldsets = [(None, {"fields": ["titel", "this_is_no_field"]})]
            errors = self.model_admin._check_fieldset_fields()
            self.assertTrue(errors)
            self.assertEqual(len(errors), 1)
            self.assertIsInstance(errors[0], checks.Error)
            self.assertEqual(
                errors[0].msg,
                "fieldset 'None' contains invalid item: 'this_is_no_field'. "
                "Audio has no field named 'this_is_no_field'",
            )

            # And an invalid lookup:
            self.model_admin.fieldsets = [(None, {"fields": ["titel__beep"]})]
            errors = self.model_admin._check_fieldset_fields()
            self.assertTrue(errors)
            self.assertEqual(len(errors), 1)
            self.assertIsInstance(errors[0], checks.Error)
            self.assertEqual(
                errors[0].msg,
                "fieldset 'None' contains invalid item: 'titel__beep'. " "Invalid lookup: beep for CharField.",
            )

            # Also check in the case when a field is actually a tuple
            # (which would be a 'forward pair' for dal):
            self.model_admin.fieldsets = [(None, {"fields": [("titel", "tracks")]})]
            self.assertFalse(self.model_admin._check_fieldset_fields())
            self.model_admin.fieldsets = [("Beep", {"fields": [("titel", "this_is_no_field")]})]
            errors = self.model_admin._check_fieldset_fields()
            self.assertTrue(errors)
            self.assertEqual(len(errors), 1)
            self.assertIsInstance(errors[0], checks.Error)
            self.assertEqual(
                errors[0].msg,
                "fieldset 'Beep' contains invalid item: '('titel', 'this_is_no_field')'. "
                "Audio has no field named 'this_is_no_field'",
            )

    def test_get_queryset(self):
        """Assert that get_queryset calls the queryset's overview method."""
        mock_overview = mock.Mock()
        with mock.patch("dbentry.admin.base.super") as super_mock:
            for mock_queryset in [mock.Mock(spec_set=True), mock.Mock(overview=mock_overview)]:
                super_mock.return_value.get_queryset.return_value = mock_queryset
                has_overview = hasattr(mock_queryset, "overview")
                with self.subTest(has_overview_attr=has_overview):
                    self.model_admin.get_queryset(self.get_request())
                    if has_overview:
                        mock_overview.assert_called()
                    else:
                        mock_overview.assert_not_called()

    def test_get_changelist(self):
        """MIZModelAdmin should use MIZChangelist."""
        self.assertEqual(self.model_admin.get_changelist(self.get_request), MIZChangeList)

    def test_get_index_category(self):
        self.assertEqual(self.model_admin.get_index_category(), "Sonstige")  # default value
        self.model_admin.index_category = "Hovercrafts"
        self.assertEqual(self.model_admin.get_index_category(), "Hovercrafts")

    def test_has_merge_permission(self):
        ct = ContentType.objects.get_for_model(self.model)
        codename = get_permission_codename("merge", self.model._meta)
        merge_perm = Permission.objects.get(content_type=ct, codename=codename)
        self.staff_user.user_permissions.add(merge_perm)

        request = RequestFactory().get("/")
        request.user = self.noperms_user
        self.assertFalse(self.model_admin.has_merge_permission(request))
        request.user = self.staff_user
        self.assertTrue(self.model_admin.has_merge_permission(request))
        request.user = self.super_user
        self.assertTrue(self.model_admin.has_merge_permission(request))

    def test_has_alter_bestand_permission(self):
        perms = []
        for action in ("add", "change", "delete"):
            ct = ContentType.objects.get_for_model(Bestand)
            codename = get_permission_codename(action, Bestand._meta)
            perms.append(Permission.objects.get(codename=codename, content_type=ct))

        self.staff_user.user_permissions.add(*perms)

        request = RequestFactory().get("/")
        with patch("dbentry.admin.base.BESTAND_MODEL_NAME", "test_admin.Bestand"):
            request.user = self.noperms_user
            self.assertFalse(self.model_admin.has_alter_bestand_permission(request))
            request.user = self.staff_user
            self.assertTrue(self.model_admin.has_alter_bestand_permission(request))
            request.user = self.super_user
            self.assertTrue(self.model_admin.has_alter_bestand_permission(request))

    def test_get_exclude(self):
        """
        get_exclude should add any concrete M2M field to the exclusion list,
        unless the ModelAdmin specifies exclude.
        """
        # tests.Veranstaltung has two concrete M2M fields and one 'reverse' M2M
        # field to Audio.
        model_admin = self.model_admin_class(Veranstaltung, self.admin_site)
        request = RequestFactory().get("/")
        excluded = model_admin.get_exclude(request)
        self.assertIn("musiker", excluded)
        self.assertIn("band", excluded)
        self.assertNotIn("audio", excluded)

        # Explicit exclude should take priority:
        model_admin.exclude = ["audio"]
        excluded = model_admin.get_exclude(request)
        self.assertNotIn("musiker", excluded)
        self.assertNotIn("band", excluded)
        self.assertIn("audio", excluded)

    def test_fieldset_includes_one_additional_fieldset(self):
        """
        get_fieldset should add an extra fieldset for the fields 'beschreibung'
        and 'bemerkungen'.
        """
        request = self.get_request(user=self.super_user)
        self.assertEqual(len(self.model_admin.get_fieldsets(request, self.obj)), 2)

    def test_get_fieldsets_adds_bb_fieldset(self):
        """
        Assert that get_fieldsets calls the _add_bb_fieldset method to include
        an extra fieldset.
        """
        with patch.object(self.model_admin, "_add_bb_fieldset") as add_bb_mock:
            self.model_admin.get_fieldsets(request=self.get_request())
            add_bb_mock.assert_called()

    def test_add_bb_fieldset(self):
        """
        The fields 'beschreibung' and 'bemerkungen' should be moved from the
        default fieldset ('None') to their own fieldset, if present in the
        default fieldset's fields.
        """
        bb_fieldset = (
            "Beschreibung & Bemerkungen",
            {"fields": ["beschreibung", "bemerkungen"], "classes": ["collapse", "collapsed"]},
        )

        # Both fields are included:
        fieldsets = self.model_admin._add_bb_fieldset([(None, {"fields": ["titel", "beschreibung", "bemerkungen"]})])
        self.assertEqual(len(fieldsets), 2)
        self.assertIn((None, {"fields": ["titel"]}), fieldsets)
        self.assertIn(bb_fieldset, fieldsets)

        # The two fields aren't included in the default fieldset:
        fieldsets = self.model_admin._add_bb_fieldset([(None, {"fields": ["titel"]})])
        self.assertEqual(len(fieldsets), 1)

    def test_add_changelist_links(self):
        links = self.model_admin.add_changelist_links(self.obj.pk)
        self.assertIn(
            {"url": f"/admin/test_admin/veranstaltung/?audio={self.obj.pk}", "label": "Veranstaltungen (1)"}, links
        )
        self.assertIn({"url": f"/admin/test_admin/band/?audio={self.obj.pk}", "label": "Bands (1)"}, links)

    def test_add_changelist_links_no_object_id(self):
        """
        Assert that add_changelist_links returns an empty list when no
        object_id was provided.
        """
        self.assertEqual(self.model_admin.add_changelist_links(object_id=None), [])

    def test_add_changelist_links_ignores_relations_with_inlines(self):
        """No changelist_links should be created for relations handled by inlines."""
        # AudioAdmin has an inline for the relation to Musiker.
        links = self.model_admin.add_changelist_links(self.obj.pk)
        _urls, labels = zip(*(d.values() for d in links))
        self.assertNotIn("Musiker (1)", labels)

    def test_add_changelist_links_m2m_relation_link(self):
        """
        The links should follow M2M relations to the *other* model of the
        relation - not back to *this* model.
        """
        # The link for Veranstaltung should point to the Veranstaltung
        # changelist - not the Audio changelist.
        links = self.model_admin.add_changelist_links(self.obj.pk)
        urls, _labels = zip(*(d.values() for d in links))
        self.assertIn(f"/admin/test_admin/veranstaltung/?audio={self.obj.pk}", urls)

    def test_add_changelist_links_prefer_labels_arg(self):
        """Passed in labels should be used over the model's verbose name."""
        links = self.model_admin.add_changelist_links(self.obj.pk, labels={"band": "Hovercrafts"})
        self.assertIn({"url": f"/admin/test_admin/band/?audio={self.obj.pk}", "label": "Hovercrafts (1)"}, links)

    def test_add_changelist_links_uses_related_name(self):
        """If the relation has a related_name, it should be used as the label."""
        rel = Audio._meta.get_field("band").remote_field
        with mock.patch.object(rel, "related_name", new="hovercrafts_full_of_eels"):
            links = self.model_admin.add_changelist_links(self.obj.pk)
            _urls, labels = zip(*(d.values() for d in links))
            self.assertIn("Hovercrafts Full Of Eels (1)", labels)

    def test_add_extra_context(self):
        """Assert that add_extra_context adds additional items for the context."""
        extra = self.model_admin.add_extra_context(object_id=self.obj.pk)
        self.assertIn("collapse_all", extra)
        self.assertIn("changelist_links", extra)

    def test_view_context(self):
        """
        Assert that the context for both add and change views include
        'collapse_all`and 'changelist_links' items.
        """
        for url in (self.add_path, self.change_path.format(pk=self.obj.pk)):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertTrue("collapse_all" in response.context)
                self.assertTrue("changelist_links" in response.context)

    def test_has_module_permission_superuser_only(self):
        """
        Only superusers should have module permission, if the superuser_only
        flag is set.
        """
        perm = Permission.objects.get(
            codename=get_permission_codename("change", self.model._meta),
            content_type=ContentType.objects.get_for_model(self.model),
        )
        self.staff_user.user_permissions.add(perm)
        request = self.get_request(user=self.staff_user)
        self.assertTrue(self.model_admin.has_module_permission(request))
        with mock.patch.object(self.model_admin, "superuser_only", True):
            self.assertFalse(self.model_admin.has_module_permission(request))

    def test_save_model(self):
        """save_model should not update the _name of a ComputedNameModel object."""
        obj = make(Person, vorname="Alice", nachname="Testman")
        obj.nachname = "Mantest"
        self.model_admin.save_model(None, obj, None, None)
        self.assertEqual(list(Person.objects.filter(pk=obj.pk).values_list("_name", flat=True)), ["Alice Testman"])

    def test_save_related(self):
        """
        save_related should force an update of the _name of a ComputedNameModel
        object.
        """
        obj = make(Person, vorname="Alice", nachname="Testman")
        obj.nachname = "Mantest"
        obj.save(update=False)
        form = mock.Mock(instance=obj)
        with mock.patch("dbentry.admin.base.super"):
            self.model_admin.save_related(None, form, [], None)

        self.assertEqual(form.instance._name, "Alice Mantest")
        self.assertEqual(list(Person.objects.filter(pk=obj.pk).values_list("_name", flat=True)), ["Alice Mantest"])

    def test_change_message_capitalized_fields(self):
        """Assert that the LogEntry/history change message uses the field labels."""
        form_class = self.model_admin.get_form(self.get_request(), obj=self.obj, change=True)
        form = form_class(data={"titel": "A different title", "tracks": "10"}, instance=self.obj)
        change_messages = self.model_admin.construct_change_message(request=None, form=form, formsets=None)

        self.assertIn("changed", change_messages[0])
        self.assertIn("fields", change_messages[0]["changed"])
        changed_fields = change_messages[0]["changed"]["fields"]
        for field in ("Titel", "Anz. Tracks"):
            with self.subTest(field=field):
                self.assertIn(field, changed_fields)

    def test_get_search_results(self):
        """
        If a search term is given, get_search_results should do call the full
        text search method of the queryset.
        """
        request = self.get_request()
        qs = self.model.objects.all()
        with mock.patch.object(qs, "search", create=True) as search_mock:
            self.model_admin.get_search_results(request, qs, search_term="")
            search_mock.assert_not_called()
            self.model_admin.get_search_results(request, qs, search_term="q")
            search_mock.assert_called()


@override_settings(ROOT_URLCONF="tests.test_admin.urls")
class ChangeConfirmationTest(AdminTestCase):
    admin_site = admin_site
    model_admin_class = PersonAdmin
    model = Person

    @classmethod
    def setUpTestData(cls):
        cls.obj = make(Person, vorname="Alice", nachname="Testman")
        super().setUpTestData()

    def test_confirmation_required(self):
        """Changes that are drastic enough should require confirmation."""
        response = self.post_response(
            self.change_path.format(pk=self.obj.pk),
            data={"vorname": "Bob", "nachname": "Testman", "_continue": ""},
            follow=True,
        )
        self.assertTemplateUsed(response, "admin/change_confirmation.html")
        self.assertNotEqual(self.obj.vorname, "Bob", msg="The object should not be changed without confirmation.")

    def test_confirmation_not_required(self):
        """Changes that are minor enough should not require confirmation."""
        response = self.post_response(
            self.change_path.format(pk=self.obj.pk),
            data={"vorname": "Alicia", "nachname": "Testman", "_continue": ""},
            follow=True,
        )
        self.assertTemplateUsed(response, "admin/change_form.html")
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.vorname, "Alicia")

    def test_change_confirmed(self):
        form_data = {"vorname": "Bob", "nachname": "Testman", "_continue": ""}
        session = self.client.session
        session["confirmed_form_data"] = form_data
        session.save()
        response = self.client.post(
            self.change_path.format(pk=self.obj.pk), data={"_change_confirmed": "True", **form_data}, follow=True
        )
        self.assertTemplateUsed(response, "admin/change_form.html")
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.vorname, "Bob")


@override_settings(ROOT_URLCONF="tests.test_admin.urls")
class ChangelistAnnotationsTest(AdminTestCase):
    admin_site = admin_site
    model_admin_class = BandAdmin
    model = Band

    @classmethod
    def setUpTestData(cls):
        cls.obj = make(Band, band_name="Black Rebel Motorcycle Club", bandalias__alias=["BRMC", "B.R.M.C."])
        super().setUpTestData()

    def test_result_list_has_annotations(self):
        """Assert that the result list has the expected annotations."""
        response = self.get_response(self.changelist_path)
        self.assertEqual(response.status_code, 200)
        self.assertIn("alias_list", response.context["cl"].result_list.query.annotations)

    def test_result_list_annotated_values(self):
        """
        Assert that the result list has the expected values for the annotated
        field.
        """
        response = self.get_response(self.changelist_path)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(["B.R.M.C.", "BRMC"], response.context["cl"].result_list[0].alias_list)

    def test_changelist_context_values(self):
        """
        Assert that the changelist template context contains the expected HTML
        for the annotated field and its values.
        """
        response = self.get_response(self.changelist_path)
        self.assertEqual(response.status_code, 200)
        self.assertIn('<td class="field-alias_string">B.R.M.C., BRMC</td>', response.context["results"][0])

    def test_ordering_by_annotation(self):
        """Assert that the annotated field can be ordered against."""
        # See commit f6bfe55e.
        index = self.model_admin.list_display.index("alias_string")
        response = self.get_response(self.changelist_path, data={"o": str(index)})
        self.assertEqual(response.status_code, 200)
        self.assertIn("alias_list", response.context["cl"].result_list.query.order_by)

    def test_pagination(self):
        """Assert that the paginated queryset is as expected (content & count)."""
        make(self.model, bandalias__extra=1)
        response = self.get_response(self.changelist_path)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["cl"].paginator.count, 2)
