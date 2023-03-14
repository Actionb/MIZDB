from django import template

register = template.Library()


@register.simple_tag
def urlname(opts, arg):
    return f"mizdb:{opts.app_label}_{opts.model_name}_{arg}"
