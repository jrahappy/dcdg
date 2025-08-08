from django import template
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def breadcrumb(*args, **kwargs):
    """
    Generate breadcrumb navigation
    Usage: {% breadcrumb "Home" "dashboard:home" "Products" "product:product_list" "Current Page" %}
    """
    if len(args) % 2 != 1:
        return ''
    
    breadcrumbs = []
    
    # Process pairs of (label, url_name)
    for i in range(0, len(args) - 1, 2):
        label = args[i]
        url_name = args[i + 1]
        
        # Replace "Dashboard" with home icon
        if label == "Dashboard":
            label = '<i class="fas fa-home"></i>'
        
        if url_name:
            try:
                if ',' in url_name:
                    # Handle URL with arguments
                    parts = url_name.split(',')
                    url_name_part = parts[0]
                    url_args = [arg.strip() for arg in parts[1:]]
                    url = reverse(url_name_part, args=url_args)
                else:
                    url = reverse(url_name)
                breadcrumbs.append(f'<a href="{url}" class="text-gray-500 hover:text-gray-700">{label}</a>')
            except:
                # If reverse fails, treat as plain text
                breadcrumbs.append(f'<span class="text-gray-500">{label}</span>')
        else:
            breadcrumbs.append(f'<span class="text-gray-500">{label}</span>')
    
    # Add the current page (last argument)
    if args:
        current_page = args[-1]
        breadcrumbs.append(f'<span class="text-gray-900">{current_page}</span>')
    
    # Build the HTML
    html_parts = []
    for i, crumb in enumerate(breadcrumbs):
        if i > 0:
            html_parts.append('<svg class="flex-shrink-0 h-5 w-5 text-gray-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd"/></svg>')
        html_parts.append(crumb)
    
    return mark_safe(' '.join(html_parts))


@register.inclusion_tag('dashboard/breadcrumb.html')
def render_breadcrumbs(breadcrumbs):
    """
    Render breadcrumbs using a template
    Usage: {% render_breadcrumbs breadcrumbs %}
    Where breadcrumbs is a list of dicts with 'label' and 'url' keys
    """
    return {'breadcrumbs': breadcrumbs}