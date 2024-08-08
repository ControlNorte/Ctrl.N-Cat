from django import template

register = template.Library()

@register.filter
def format_date(value):
    return value.strftime('%d/%m/%Y')

@register.filter
def format_currency(value):
    return f"R$ {value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')