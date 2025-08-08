from django import forms
from .models import EmailTemplate


class EmailTemplateForm(forms.ModelForm):
    class Meta:
        model = EmailTemplate
        fields = [
            'title',
            'subject', 
            'sender_email',
            'sender_name',
            'content_type',
            'html_content',
            'plain_content',
            'status',
            'track_opens',
            'track_clicks',
        ]
        
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
                'placeholder': 'e.g., Welcome Email, Monthly Newsletter'
            }),
            'subject': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
                'placeholder': 'e.g., Welcome to {{company_name}}!'
            }),
            'sender_name': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
                'placeholder': 'Optional: Override sender name'
            }),
            'sender_email': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
            'content_type': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
            'status': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
            'html_content': forms.Textarea(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
                'rows': 15,
                'placeholder': 'HTML content with variables like {{first_name}}'
            }),
            'plain_content': forms.Textarea(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
                'rows': 15,
                'placeholder': 'Plain text content with variables like {{first_name}}'
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        content_type = cleaned_data.get('content_type')
        html_content = cleaned_data.get('html_content')
        plain_content = cleaned_data.get('plain_content')
        
        # Validate content based on content type
        if content_type == 'html' and not html_content:
            raise forms.ValidationError('HTML content is required for HTML templates.')
        
        if content_type == 'plain' and not plain_content:
            raise forms.ValidationError('Plain text content is required for plain text templates.')
        
        if content_type == 'both':
            if not html_content and not plain_content:
                raise forms.ValidationError('At least one content type (HTML or Plain text) is required.')
        
        return cleaned_data