from django.contrib import admin
from django_summernote.admin import SummernoteModelAdmin
from .models import Category, Tag, Post, Comment


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['name']


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['name']


@admin.register(Post)
class PostAdmin(SummernoteModelAdmin):
    summernote_fields = ('content',)
    list_display = ['title', 'author', 'category', 'status', 'featured', 'published_date', 'views']
    list_filter = ['status', 'featured', 'allow_comments', 'created_at', 'published_date', 'category']
    search_fields = ['title', 'excerpt', 'content', 'author__username', 'author__email']
    prepopulated_fields = {'slug': ('title',)}
    raw_id_fields = ['author']
    date_hierarchy = 'published_date'
    ordering = ['-published_date', '-created_at']
    
    fieldsets = (
        ('Content', {
            'fields': ('title', 'slug', 'author', 'excerpt', 'content', 'featured_image')
        }),
        ('Categorization', {
            'fields': ('category', 'tags')
        }),
        ('Publishing', {
            'fields': ('status', 'published_date', 'featured', 'allow_comments')
        }),
        ('Metrics', {
            'fields': ('views', 'likes'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('author', 'category').prefetch_related('tags')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['post', 'author', 'created_at', 'is_approved', 'parent']
    list_filter = ['is_approved', 'created_at']
    search_fields = ['content', 'author__username', 'post__title']
    raw_id_fields = ['post', 'author', 'parent']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    actions = ['approve_comments', 'disapprove_comments']
    
    def approve_comments(self, request, queryset):
        queryset.update(is_approved=True)
        self.message_user(request, f'{queryset.count()} comments approved.')
    approve_comments.short_description = 'Approve selected comments'
    
    def disapprove_comments(self, request, queryset):
        queryset.update(is_approved=False)
        self.message_user(request, f'{queryset.count()} comments disapproved.')
    disapprove_comments.short_description = 'Disapprove selected comments'
