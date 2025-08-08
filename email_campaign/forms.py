from django import forms
from .models import EmailCampaign, PeriodicCampaign
from email_templates.models import EmailTemplate


class EmailCampaignForm(forms.ModelForm):
    class Meta:
        model = EmailCampaign
        fields = ['name', 'subject', 'content', 'from_email']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Q1 2024 Medical Clinic Newsletter'
            }),
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Important Updates for Your Dental Practice'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 10,
                'placeholder': 'Write your email content here...'
            }),
            'from_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Leave blank to use default'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['from_email'].required = False
        self.fields['name'].required = True
        self.fields['subject'].required = True
        self.fields['content'].required = True


class PeriodicCampaignForm(forms.ModelForm):
    email_template = forms.ModelChoiceField(
        queryset=EmailTemplate.objects.filter(status='active'),
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
        })
    )
    
    class Meta:
        model = PeriodicCampaign
        fields = [
            'name', 'description', 'target_group', 'email_template',
            'target_link', 'target_link_parameter', 'frequency',
            'start_date', 'end_date'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
                'placeholder': 'e.g., Weekly Newsletter'
            }),
            'description': forms.Textarea(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
                'rows': 3,
                'placeholder': 'Describe the purpose of this periodic campaign'
            }),
            'target_group': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
            'target_link': forms.URLInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
                'placeholder': 'https://example.com/special-offer'
            }),
            'target_link_parameter': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
                'placeholder': 'utm_source=email&utm_campaign=periodic'
            }),
            'frequency': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
                'type': 'date'
            })
        }


class PeriodicCampaignEditForm(PeriodicCampaignForm):
    """Form for editing periodic campaigns (includes status field)"""
    class Meta(PeriodicCampaignForm.Meta):
        fields = PeriodicCampaignForm.Meta.fields + ['status']
        widgets = PeriodicCampaignForm.Meta.widgets.copy()
        widgets['status'] = forms.Select(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
        })