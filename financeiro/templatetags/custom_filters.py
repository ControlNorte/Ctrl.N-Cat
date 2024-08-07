from django import template
import locale

register = template.Library()

@register.filter
def format_date(value):
    return value.strftime('%d/%m/%Y')

@register.filter
def format_currency(value):
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
    return locale.currency(value, grouping=True)