from django import forms
from django_summernote.widgets import SummernoteWidget
from .models import Post, Comment, Category, Tag


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'slug', 'category', 'tags', 'excerpt', 'content', 'featured_image', 'status', 'allow_comments', 'featured']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'slug': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'category': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'tags': forms.SelectMultiple(attrs={'class': 'select select-bordered w-full', 'size': '5'}),
            'excerpt': forms.Textarea(attrs={'rows': 3, 'class': 'textarea textarea-bordered w-full'}),
            'content': SummernoteWidget(),
            'featured_image': forms.FileInput(attrs={'class': 'file-input file-input-bordered w-full'}),
            'status': forms.Select(attrs={'class': 'select select-bordered w-full'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['slug'].required = False
        self.fields['tags'].required = False
        self.fields['category'].required = False
        self.fields['featured_image'].required = False


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 3,
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'Write your comment here...'
            })
        }