from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Q, Count
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Post, Category, Tag, Comment
from .forms import PostForm, CommentForm

User = get_user_model()


class PostListView(ListView):
    model = Post
    template_name = 'blog/post_list.html'
    context_object_name = 'posts'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = Post.objects.filter(status='published').select_related('author', 'category').prefetch_related('tags')
        
        # Search functionality
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(excerpt__icontains=search_query) |
                Q(content__icontains=search_query)
            )
        
        # Category filter
        category_slug = self.request.GET.get('category')
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        
        # Tag filter
        tag_slug = self.request.GET.get('tag')
        if tag_slug:
            queryset = queryset.filter(tags__slug=tag_slug)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.annotate(post_count=Count('posts'))
        context['popular_tags'] = Tag.objects.annotate(post_count=Count('posts')).order_by('-post_count')[:10]
        context['recent_posts'] = Post.objects.filter(status='published').order_by('-published_date')[:5]
        return context


class PostDetailView(DetailView):
    model = Post
    template_name = 'blog/post_detail.html'
    context_object_name = 'post'
    
    def get_queryset(self):
        # Allow authors to view their own draft posts
        if self.request.user.is_authenticated:
            return Post.objects.filter(
                Q(status='published') | Q(author=self.request.user)
            ).select_related('author', 'category').prefetch_related('tags', 'comments')
        return Post.objects.filter(status='published').select_related('author', 'category').prefetch_related('tags', 'comments')
    
    def get_object(self):
        obj = super().get_object()
        obj.increment_views()
        return obj
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['comments'] = self.object.comments.filter(is_approved=True, parent=None).select_related('author')
        context['comment_form'] = CommentForm()
        context['related_posts'] = Post.objects.filter(
            status='published',
            category=self.object.category
        ).exclude(id=self.object.id)[:3]
        context['is_liked'] = False
        if self.request.user.is_authenticated:
            context['is_liked'] = self.object.likes.filter(id=self.request.user.id).exists()
        return context


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/post_form.html'
    
    def form_valid(self, form):
        form.instance.author = self.request.user
        messages.success(self.request, 'Post created successfully!')
        return super().form_valid(form)


class PostUpdateView(LoginRequiredMixin, UpdateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/post_form.html'
    
    def get_queryset(self):
        # Authors can edit their own posts regardless of status
        return Post.objects.filter(author=self.request.user)
    
    def form_valid(self, form):
        messages.success(self.request, 'Post updated successfully!')
        return super().form_valid(form)


class PostDeleteView(LoginRequiredMixin, DeleteView):
    model = Post
    template_name = 'blog/post_confirm_delete.html'
    success_url = reverse_lazy('blog:post-list')
    
    def get_queryset(self):
        return Post.objects.filter(author=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Post deleted successfully!')
        return super().delete(request, *args, **kwargs)


@login_required
def add_comment(request, pk):
    post = get_object_or_404(Post, pk=pk, status='published')
    
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            
            # Handle reply
            parent_id = request.POST.get('parent_id')
            if parent_id:
                parent_comment = get_object_or_404(Comment, id=parent_id)
                comment.parent = parent_comment
            
            comment.save()
            messages.success(request, 'Comment added successfully!')
            return redirect('blog:post-detail', pk=post.pk)
    
    return redirect('blog:post-detail', pk=post.pk)


@login_required
def publish_post(request, pk):
    post = get_object_or_404(Post, pk=pk, author=request.user, status='draft')
    
    if request.method == 'POST':
        post.status = 'published'
        post.published_date = timezone.now()
        post.save()
        messages.success(request, 'Post published successfully!')
        return redirect('blog:post-detail', pk=post.pk)
    
    return redirect('blog:post-detail', pk=post.pk)


@login_required
def like_post(request, pk):
    post = get_object_or_404(Post, pk=pk, status='published')
    
    if request.user in post.likes.all():
        post.likes.remove(request.user)
        liked = False
    else:
        post.likes.add(request.user)
        liked = True
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'liked': liked,
            'like_count': post.like_count
        })
    
    return redirect('blog:post-detail', pk=post.pk)


class CategoryDetailView(ListView):
    model = Post
    template_name = 'blog/category_detail.html'
    context_object_name = 'posts'
    paginate_by = 10
    
    def get_queryset(self):
        self.category = get_object_or_404(Category, slug=self.kwargs['slug'])
        return Post.objects.filter(status='published', category=self.category).select_related('author')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        return context


class TagDetailView(ListView):
    model = Post
    template_name = 'blog/tag_detail.html'
    context_object_name = 'posts'
    paginate_by = 10
    
    def get_queryset(self):
        self.tag = get_object_or_404(Tag, slug=self.kwargs['slug'])
        return Post.objects.filter(status='published', tags=self.tag).select_related('author', 'category')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tag'] = self.tag
        return context


class UserPostListView(ListView):
    model = Post
    template_name = 'blog/user_posts.html'
    context_object_name = 'posts'
    paginate_by = 10
    
    def get_queryset(self):
        self.user = get_object_or_404(User, username=self.kwargs['username'])
        # If viewing own posts, show drafts too
        if self.request.user.is_authenticated and self.request.user == self.user:
            return Post.objects.filter(author=self.user).select_related('category')
        return Post.objects.filter(author=self.user, status='published').select_related('category')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['author'] = self.user
        
        # Add post counts for stats
        if self.request.user.is_authenticated and self.request.user == self.user:
            all_posts = Post.objects.filter(author=self.user)
            context['total_posts'] = all_posts.count()
            context['published_posts'] = all_posts.filter(status='published').count()
            context['draft_posts'] = all_posts.filter(status='draft').count()
        
        return context
