from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json

from .models import EmailTemplate, EmailTemplateVariables
from .forms import EmailTemplateForm
from accounts.models import SenderEmail


@staff_member_required
def template_list(request):
    """List all email templates with filtering"""
    templates = EmailTemplate.objects.all()
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        templates = templates.filter(
            Q(title__icontains=search_query) |
            Q(subject__icontains=search_query) |
            Q(html_content__icontains=search_query) |
            Q(plain_content__icontains=search_query)
        )
    
    # Status filter
    status_filter = request.GET.get('status', '')
    if status_filter:
        templates = templates.filter(status=status_filter)
    
    # Content type filter
    content_type_filter = request.GET.get('content_type', '')
    if content_type_filter:
        templates = templates.filter(content_type=content_type_filter)
    
    # Pagination
    paginator = Paginator(templates, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get statistics
    total_templates = EmailTemplate.objects.count()
    active_templates = EmailTemplate.objects.filter(status='active').count()
    marketing_count = EmailTemplate.objects.filter(content_type='marketing').count()
    transactional_count = EmailTemplate.objects.filter(content_type='transactional').count()
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'content_type_filter': content_type_filter,
        'status_choices': EmailTemplate.STATUS_CHOICES,
        'content_type_choices': EmailTemplate.CONTENT_TYPE_CHOICES,
        'total_templates': total_templates,
        'active_templates': active_templates,
        'marketing_count': marketing_count,
        'transactional_count': transactional_count,
        'is_paginated': page_obj.has_other_pages(),
    }
    
    return render(request, 'email_templates/email_template_list_daisyui.html', context)


@staff_member_required
def template_create(request):
    """Create a new email template"""
    if request.method == 'POST':
        form = EmailTemplateForm(request.POST)
        if form.is_valid():
            template = form.save(commit=False)
            template.created_by = request.user
            
            # Set default available variables
            if not template.available_variables:
                template.available_variables = template.get_default_variables()
            
            template.save()
            
            # Create default variables for the new template
            default_vars = template.get_default_variables()
            for var_name, description in default_vars.items():
                # Determine appropriate type based on variable name
                var_type = 'text'
                if var_name == 'email':
                    var_type = 'email'
                elif var_name in ['unsubscribe_link', 'target_link']:
                    var_type = 'url'
                elif var_name == 'current_year':
                    var_type = 'number'
                elif var_name == 'current_date':
                    var_type = 'date'
                
                # Create the variable
                EmailTemplateVariables.objects.create(
                    template=template,
                    name=var_name,
                    type=var_type,
                    description=description,
                    is_required=False,  # Default variables are optional
                    default_value=''
                )
            
            messages.success(request, 'Email template created successfully with default variables!')
            return redirect('email_templates:template_detail', pk=template.pk)
    else:
        form = EmailTemplateForm()
    
    # Get sender emails for the form
    sender_emails = SenderEmail.objects.filter(is_verified=True)
    
    context = {
        'form': form,
        'sender_emails': sender_emails,
        'is_create': True,
    }
    
    return render(request, 'email_templates/template_form.html', context)


@staff_member_required
def template_edit(request, pk):
    """Edit an existing email template"""
    template = get_object_or_404(EmailTemplate, pk=pk)
    
    if request.method == 'POST':
        form = EmailTemplateForm(request.POST, instance=template)
        if form.is_valid():
            form.save()
            messages.success(request, 'Email template updated successfully!')
            return redirect('email_templates:template_detail', pk=template.pk)
    else:
        form = EmailTemplateForm(instance=template)
    
    # Get sender emails for the form
    sender_emails = SenderEmail.objects.filter(is_verified=True)
    
    # Get existing variables for this template
    variables = template.variables.all()
    default_variables = template.get_default_variables()
    
    context = {
        'form': form,
        'template': template,
        'sender_emails': sender_emails,
        'variables': variables,
        'default_variables': default_variables,
        'is_create': False,
    }
    
    return render(request, 'email_templates/template_form.html', context)


@staff_member_required
def template_detail(request, pk):
    """View email template details"""
    template = get_object_or_404(EmailTemplate, pk=pk)
    
    context = {
        'template': template,
    }
    
    return render(request, 'email_templates/template_detail_daisyui.html', context)


@staff_member_required
def template_preview(request, pk):
    """Preview email template with sample data"""
    template = get_object_or_404(EmailTemplate, pk=pk)
    
    # Get custom variables for this template
    custom_variables = template.variables.all()
    
    # Build sample data including default and custom variables
    sample_data = {
        'first_name': 'John',
        'last_name': 'Doe',
        'email': 'john.doe@example.com',
        'company_name': 'Acme Dental Clinic',
        'unsubscribe_link': '#',
        'target_link': 'https://example.com/special-offer',
        'current_year': '2025',
        'current_date': 'August 1, 2025',
    }
    
    # Add custom variables with their default values or sample values
    for var in custom_variables:
        if var.default_value:
            sample_data[var.name] = var.default_value
        else:
            # Generate sample value based on type
            if var.type == 'text':
                sample_data[var.name] = f'Sample {var.name}'
            elif var.type == 'number':
                sample_data[var.name] = '123'
            elif var.type == 'date':
                sample_data[var.name] = 'January 1, 2025'
            elif var.type == 'url':
                sample_data[var.name] = 'https://example.com'
            elif var.type == 'email':
                sample_data[var.name] = 'sample@example.com'
            elif var.type == 'boolean':
                sample_data[var.name] = 'Yes'
            elif var.type == 'choice' and var.choices:
                sample_data[var.name] = var.choices[0] if var.choices else 'Choice 1'
    
    # Replace variables in content
    html_preview = template.html_content
    plain_preview = template.plain_content
    subject_preview = template.subject
    
    for var, value in sample_data.items():
        placeholder = f'{{{{{var}}}}}'
        html_preview = html_preview.replace(placeholder, str(value))
        plain_preview = plain_preview.replace(placeholder, str(value))
        subject_preview = subject_preview.replace(placeholder, str(value))
    
    context = {
        'template': template,
        'html_preview': html_preview,
        'plain_preview': plain_preview,
        'subject_preview': subject_preview,
        'sample_data': sample_data,
        'custom_variables': custom_variables,
    }
    
    return render(request, 'email_templates/template_preview_daisyui.html', context)


@staff_member_required
@require_POST
def template_delete(request, pk):
    """Delete an email template"""
    template = get_object_or_404(EmailTemplate, pk=pk)
    
    if request.method == 'POST':
        template.delete()
        messages.success(request, 'Email template deleted successfully!')
        return redirect('email_templates:template_list')
    
    return redirect('email_templates:template_detail', pk=pk)


@staff_member_required
@require_POST
def template_duplicate(request, pk):
    """Duplicate an email template"""
    template = get_object_or_404(EmailTemplate, pk=pk)
    
    # Create a copy
    new_template = EmailTemplate(
        title=f"{template.title} (Copy)",
        subject=template.subject,
        sender_email=template.sender_email,
        sender_name=template.sender_name,
        content_type=template.content_type,
        html_content=template.html_content,
        plain_content=template.plain_content,
        status='draft',  # Always set to draft
        created_by=request.user,
        available_variables=template.available_variables,
        track_opens=template.track_opens,
        track_clicks=template.track_clicks,
    )
    new_template.save()
    
    # Duplicate all variables from the original template
    original_variables = template.variables.all()
    for var in original_variables:
        EmailTemplateVariables.objects.create(
            template=new_template,
            name=var.name,
            type=var.type,
            length=var.length,
            description=var.description,
            default_value=var.default_value,
            is_required=var.is_required,
            choices=var.choices
        )
    
    messages.success(request, 'Email template duplicated successfully with all variables!')
    return redirect('email_templates:template_edit', pk=new_template.pk)


@staff_member_required
def template_variables(request):
    """API endpoint to get template variables"""
    default_vars = EmailTemplate().get_default_variables()
    
    return JsonResponse({
        'variables': [
            {'name': var, 'description': desc}
            for var, desc in default_vars.items()
        ]
    })


# EmailTemplateVariables CRUD views
@staff_member_required
def variable_create(request, template_pk):
    """Create a new variable for a template via AJAX"""
    template = get_object_or_404(EmailTemplate, pk=template_pk)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Validate required fields
            if not data.get('name'):
                return JsonResponse({'error': 'Variable name is required'}, status=400)
            
            # Check if variable already exists
            if template.variables.filter(name=data['name']).exists():
                return JsonResponse({'error': 'Variable with this name already exists'}, status=400)
            
            # Create the variable
            variable = EmailTemplateVariables.objects.create(
                template=template,
                name=data['name'],
                type=data.get('type', 'text'),
                length=data.get('length') or None,
                description=data.get('description', ''),
                default_value=data.get('default_value', ''),
                is_required=data.get('is_required', True),
                choices=data.get('choices', [])
            )
            
            return JsonResponse({
                'id': variable.id,
                'name': variable.name,
                'type': variable.type,
                'length': variable.length,
                'description': variable.description,
                'default_value': variable.default_value,
                'is_required': variable.is_required,
                'choices': variable.choices,
                'tag': variable.get_variable_tag()
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@staff_member_required
def variable_update(request, template_pk, variable_pk):
    """Update a variable via AJAX"""
    template = get_object_or_404(EmailTemplate, pk=template_pk)
    variable = get_object_or_404(EmailTemplateVariables, pk=variable_pk, template=template)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Update fields
            if 'name' in data and data['name'] != variable.name:
                # Check if new name already exists
                if template.variables.filter(name=data['name']).exclude(pk=variable.pk).exists():
                    return JsonResponse({'error': 'Variable with this name already exists'}, status=400)
                variable.name = data['name']
            
            if 'type' in data:
                variable.type = data['type']
            if 'length' in data:
                variable.length = data['length'] or None
            if 'description' in data:
                variable.description = data['description']
            if 'default_value' in data:
                variable.default_value = data['default_value']
            if 'is_required' in data:
                variable.is_required = data['is_required']
            if 'choices' in data:
                variable.choices = data['choices']
            
            variable.save()
            
            return JsonResponse({
                'id': variable.id,
                'name': variable.name,
                'type': variable.type,
                'length': variable.length,
                'description': variable.description,
                'default_value': variable.default_value,
                'is_required': variable.is_required,
                'choices': variable.choices,
                'tag': variable.get_variable_tag()
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@staff_member_required
@require_POST
def variable_delete(request, template_pk, variable_pk):
    """Delete a variable via AJAX"""
    template = get_object_or_404(EmailTemplate, pk=template_pk)
    variable = get_object_or_404(EmailTemplateVariables, pk=variable_pk, template=template)
    
    variable.delete()
    return JsonResponse({'success': True})


@staff_member_required
def variable_list(request, template_pk):
    """Get all variables for a template via AJAX"""
    template = get_object_or_404(EmailTemplate, pk=template_pk)
    
    variables = [{
        'id': var.id,
        'name': var.name,
        'type': var.type,
        'length': var.length,
        'description': var.description,
        'default_value': var.default_value,
        'is_required': var.is_required,
        'choices': var.choices,
        'tag': var.get_variable_tag()
    } for var in template.variables.all()]
    
    return JsonResponse({'variables': variables})


# 2-Step Email Template Creation Process

@staff_member_required
def template_create_step1(request):
    """Step 1: Create basic email template"""
    if request.method == 'POST':
        form = EmailTemplateForm(request.POST)
        if form.is_valid():
            template = form.save(commit=False)
            template.created_by = request.user
            
            # Set default available variables
            if not template.available_variables:
                template.available_variables = template.get_default_variables()
            
            template.save()
            
            # Store template ID in session for step 2
            request.session['template_creation'] = {
                'template_id': template.id,
                'step': 1
            }
            
            messages.success(request, 'Email template created! Now add custom variables.')
            return redirect('email_templates:template_create_step2')
    else:
        form = EmailTemplateForm()
    
    # Get sender emails for the form
    sender_emails = SenderEmail.objects.filter(is_verified=True)
    
    context = {
        'form': form,
        'sender_emails': sender_emails,
        'step': 1,
        'step_title': 'Basic Template Information'
    }
    
    return render(request, 'email_templates/template_create_step1.html', context)


@staff_member_required
def template_create_step2(request):
    """Step 2: Add template variables"""
    # Check if step 1 is completed
    creation_data = request.session.get('template_creation')
    if not creation_data or creation_data.get('step', 0) < 1:
        messages.error(request, 'Please complete step 1 first.')
        return redirect('email_templates:template_create_step1')
    
    # Get the template created in step 1
    template = get_object_or_404(EmailTemplate, id=creation_data['template_id'])
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'finish':
            # Clear session data and finish
            if 'template_creation' in request.session:
                del request.session['template_creation']
            
            messages.success(request, f'Email template "{template.title}" created successfully!')
            return redirect('email_templates:template_detail', pk=template.id)
        
        elif action == 'skip_and_finish':
            # Create default variables and finish
            default_vars = template.get_default_variables()
            for var_name, description in default_vars.items():
                # Skip if variable already exists
                if not template.variables.filter(name=var_name).exists():
                    # Determine appropriate type based on variable name
                    var_type = 'text'
                    if var_name == 'email':
                        var_type = 'email'
                    elif var_name in ['unsubscribe_link', 'target_link']:
                        var_type = 'url'
                    elif var_name == 'current_year':
                        var_type = 'number'
                    elif var_name == 'current_date':
                        var_type = 'date'
                    
                    # Create the variable
                    EmailTemplateVariables.objects.create(
                        template=template,
                        name=var_name,
                        type=var_type,
                        description=description,
                        is_required=False,  # Default variables are optional
                        default_value=''
                    )
            
            # Clear session data and finish
            if 'template_creation' in request.session:
                del request.session['template_creation']
            
            messages.success(request, f'Email template "{template.title}" created with default variables!')
            return redirect('email_templates:template_detail', pk=template.id)
    
    # Get existing variables for this template
    variables = template.variables.all()
    default_variables = template.get_default_variables()
    
    context = {
        'template': template,
        'variables': variables,
        'default_variables': default_variables,
        'step': 2,
        'step_title': 'Template Variables'
    }
    
    return render(request, 'email_templates/template_create_step2.html', context)