from django import template

register = template.Library()


@register.inclusion_tag("help/includes/image_modal.html")
def image_modal(image_name, caption):
    """
    Render a single image, ready to be displayed in full-size in a modal.

    Example:
        {% image_modal 'foo.png' 'Foo' %}
    """
    return {"image_name": image_name, "caption": caption}


@register.simple_tag()
def gallery_args(image_name, caption=""):
    """
    Prepare arguments for the ``image_gallery`` tag.

    Example:
        {% gallery_args 'foo.png' 'Foo' as image1 %}
        {% gallery_args 'bar.png' 'Bar' as image2 %}
        {% image_gallery image1 image2 %}
    """
    return image_name, caption


@register.inclusion_tag("help/includes/image_gallery.html")
def image_gallery(*images):
    """
    Render the given images as a gallery.

    ``images`` should be a list of 2-tuples: (image_name, caption)

    Example:
        {% gallery_args 'foo.png' 'Foo' as image1 %}
        {% gallery_args 'bar.png' 'Bar' as image2 %}
        {% image_gallery image1 image2 %}
    """
    return {"images": images}
