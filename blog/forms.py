from django import forms
from .models import Post, Comment, Category, Tag
from product.models import Category as ProductCategory, Product


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'slug', 'category', 'tags', 'excerpt', 'content', 'featured_image', 
                  'product_category', 'related_products', 'status', 'allow_comments', 'featured']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'slug': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'category': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'tags': forms.SelectMultiple(attrs={'class': 'select select-bordered w-full', 'size': '5'}),
            'excerpt': forms.Textarea(attrs={'rows': 3, 'class': 'textarea textarea-bordered w-full'}),
            'content': forms.Textarea(attrs={'rows': 10, 'class': 'textarea textarea-bordered w-full'}),
            'featured_image': forms.FileInput(attrs={'class': 'file-input file-input-bordered w-full'}),
            'product_category': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'related_products': forms.SelectMultiple(attrs={'class': 'select select-bordered w-full', 'size': '5'}),
            'status': forms.Select(attrs={'class': 'select select-bordered w-full'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['slug'].required = False
        self.fields['tags'].required = False
        self.fields['category'].required = False
        self.fields['featured_image'].required = False
        self.fields['product_category'].required = False
        self.fields['related_products'].required = False
        
        # Add helpful labels and help text
        self.fields['product_category'].label = 'Related Product Category'
        self.fields['product_category'].help_text = 'Optional: Select a product category this post relates to'
        self.fields['related_products'].label = 'Related Products'
        self.fields['related_products'].help_text = 'Optional: Select products to showcase with this post'
        
        # Optimize queryset for related products
        self.fields['related_products'].queryset = Product.objects.filter(
            status='active'
        ).select_related('category').order_by('name')
        
        # Optimize queryset for product category
        self.fields['product_category'].queryset = ProductCategory.objects.filter(
            is_active=True
        ).order_by('name')


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