from unittest.mock import Mock, patch

from django.db import models
from import_export.resources import ModelResource

from dbentry.site.views.export import BaseExportView, ExportActionView
from tests.case import ViewTestCase
from tests.model_factory import make
from tests.test_site.models import Band


class DummyModel(models.Model):
    foo = models.CharField(max_length=100)
    bar = models.CharField(max_length=100)


class BandResource(ModelResource):
    class Meta:
        model = Band


class TestBaseExportView(ViewTestCase):
    view_class = BaseExportView

    @patch("dbentry.site.views.export.super")
    def test_get_context_data_adds_queryset(self, super_mock):
        """Assert that get_context_data adds the queryset to the template context."""
        super_mock.return_value.get_context_data.return_value = {}
        queryset_mock = Mock()
        view = self.get_view(self.post_request(), queryset=queryset_mock, model=DummyModel)
        context_data = view.get_context_data()
        self.assertIn("queryset", context_data)
        self.assertEqual(context_data["queryset"], queryset_mock)

    @patch("dbentry.site.views.export.super")
    def test_get_form_kwarg_adds_choices(self, super_mock):
        """
        Assert that get_form_kwargs adds the expected choices for the
        fields_select field.
        """

        def get_verbose_name_mock(resource, field_name):
            return field_name.capitalize()

        super_mock.return_value.get_form_kwargs.return_value = {}
        resource_mock = Mock()
        resource_mock.get_export_order.return_value = ["foo", "bar"]
        view = self.get_view(self.post_request(), queryset=Mock(), model=DummyModel)
        with patch.object(view, "get_export_resource", new=Mock(return_value=resource_mock)):
            with patch("dbentry.site.views.export.get_verbose_name_for_resource_field", new=get_verbose_name_mock):
                form_kwargs = view.get_form_kwargs()
                self.assertEqual(form_kwargs["choices"]["fields_select"], [("foo", "Foo"), ("bar", "Bar")])

    def test_get_export_resource_fields_from_form(self):
        """
        Assert that get_export_resource_fields_from_form returns the cleaned
        data of the fields_select formfield.
        """
        form_mock = Mock(cleaned_data={"fields_select": ["foo", "bar"], "something_else": "1"})
        view = self.get_view(self.post_request(), queryset=Mock(), model=DummyModel)
        self.assertEqual(view.get_export_resource_fields_from_form(form_mock), ["foo", "bar"])

    def test_form_valid(self):
        """Assert that form_valid returns the expected response."""
        request = self.post_request(data={"fields_select": ["id", "name"], "format": "0"})
        band = make(Band, name="Foo Fighters", alias="FF")
        queryset = Band.objects.all()
        view = self.get_view(request, queryset=queryset, model=Band, resource_classes=[BandResource])
        form = view.get_form()
        assert form.is_valid()
        with patch.object(view, "get_export_filename", new=Mock(return_value="export.csv")):
            response = view.form_valid(form)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get("Content-Disposition"), 'attachment; filename="export.csv"')
        self.assertEqual(response.content.decode("utf-8"), f"id,name\r\n{band.pk},Foo Fighters\r\n")


class TestExportActionView(ViewTestCase):
    view_class = ExportActionView

    def test_post_calls_get_if_action_not_confirmed(self):
        request = self.post_request()
        view = self.get_view(request, model=DummyModel, queryset=Mock())
        with patch.object(view, "action_confirmed", new=Mock(return_value=False)):
            with patch.object(view, "get") as get_mock:
                view.post(request)
                get_mock.assert_called()

    @patch("dbentry.site.views.export.super")
    def test_post_calls_post_if_action_confirmed(self, super_mock):
        request = self.post_request()
        view = self.get_view(request, model=DummyModel, queryset=Mock())
        post_mock = Mock()
        super_mock.return_value.post = post_mock
        with patch.object(view, "action_confirmed", new=Mock(return_value=True)):
            view.post(request)
            post_mock.assert_called()
