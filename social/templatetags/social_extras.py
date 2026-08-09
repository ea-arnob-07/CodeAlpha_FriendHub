from django import template

register = template.Library()


@register.filter
def contains(collection, value):
    try:
        return value in collection
    except TypeError:
        return False

