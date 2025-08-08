from django import forms
from .models import ChatRoom, ChatMessage


class ChatRoomForm(forms.ModelForm):
    """Form for creating a new chat room"""
    class Meta:
        model = ChatRoom
        fields = ['subject']
        widgets = {
            'subject': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm',
                'placeholder': 'What would you like to discuss?',
                'required': True
            })
        }


class ChatMessageForm(forms.ModelForm):
    """Form for sending a chat message"""
    class Meta:
        model = ChatMessage
        fields = ['content', 'attachment']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm',
                'placeholder': 'Type your message...',
                'rows': 3,
                'required': True
            }),
            'attachment': forms.FileInput(attrs={
                'class': 'block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100',
                'accept': 'image/*,.pdf,.doc,.docx,.xls,.xlsx'
            })
        }