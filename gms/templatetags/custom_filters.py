from django import template
from django.middleware.csrf import get_token

register = template.Library()

@register.simple_tag(takes_context=True)
def csrf_token_value(context):
    """
    Get the CSRF token value.
    """
    request = context['request']
    return get_token(request)
