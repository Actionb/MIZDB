from django import forms


class MIZURLInput(forms.URLInput):
    """An URLInput widget with a clickable link to the URL."""

    input_type = "text"
    template_name = "mizdb/widgets/url.html"

    def build_attrs(self, base_attrs, extra_attrs=None):
        attrs = super().build_attrs(base_attrs, extra_attrs)
        # By default, if rendered with django bootstrap, the input element
        # will have display: block. To have the link on the same line as the
        # input, the input must be an inline element.
        attrs["class"] = f"{attrs.get('class', '')} d-inline".strip()
        return attrs
