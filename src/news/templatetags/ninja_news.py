from django import template

register = template.Library()

@register.filter
def date_filter(date):
    return date.strftime("%Y-%m-%d")
