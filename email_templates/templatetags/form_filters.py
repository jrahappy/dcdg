from django import template
from django.forms.widgets import Widget

register = template.Library()


@register.filter
def add_class(field, css_class):
    """
    Add CSS class to form field widget
    Usage: {{ form.field|add_class:"form-control" }}
    """
    if hasattr(field, 'as_widget'):
        # This is a BoundField
        return field.as_widget(attrs={'class': css_class})
    elif hasattr(field, 'widget'):
        # This is a Field
        field.widget.attrs.update({'class': css_class})
        return field
    else:
        # Return as-is if it's not a form field
        return field


@register.filter
def add_attrs(field, attrs_string):
    """
    Add multiple attributes to form field widget
    Usage: {{ form.field|add_attrs:"class:form-control,placeholder:Enter value" }}
    """
    if not hasattr(field, 'as_widget'):
        return field
    
    attrs = {}
    if attrs_string:
        for attr in attrs_string.split(','):
            if ':' in attr:
                key, value = attr.split(':', 1)
                attrs[key.strip()] = value.strip()
    
    return field.as_widget(attrs=attrs)