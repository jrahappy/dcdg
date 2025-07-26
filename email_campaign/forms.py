from django import forms
from .models import EmailCampaign


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