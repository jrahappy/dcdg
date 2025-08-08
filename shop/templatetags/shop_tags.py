from django import template

register = template.Library()

@register.filter
def range_filter(value):
    """Generate a range for template loops"""
    try:
        return range(1, int(value) + 1)
    except (ValueError, TypeError):
        return range(1, 11)  # Default to 1-10