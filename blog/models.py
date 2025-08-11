from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

User = get_user_model()


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("blog:category-detail", kwargs={"slug": self.slug})


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Post(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("published", "Published"),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="blog_posts"
    )
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="posts"
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="posts")

    excerpt = models.TextField(
        max_length=500, help_text="Brief description of the post"
    )
    content = models.TextField()
    featured_image = models.ImageField(upload_to="blog/images/", blank=True, null=True)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft")
    published_date = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    views = models.PositiveIntegerField(default=0)
    likes = models.ManyToManyField(User, blank=True, related_name="liked_posts")

    allow_comments = models.BooleanField(default=True)
    featured = models.BooleanField(default=False)
    product_category = models.ForeignKey(
        "product.Category", on_delete=models.SET_NULL, null=True, blank=True
    )
    related_products = models.ManyToManyField("product.Product", blank=True)

    class Meta:
        ordering = ["-published_date", "-created_at"]
        indexes = [
            models.Index(fields=["-published_date"]),
            models.Index(fields=["slug"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)

        # Set published date when status changes to published
        if self.status == "published" and not self.published_date:
            self.published_date = timezone.now()

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("blog:post-detail", kwargs={"pk": self.pk})

    @property
    def is_published(self):
        return self.status == "published"

    @property
    def like_count(self):
        return self.likes.count()

    def increment_views(self):
        self.views += 1
        self.save(update_fields=["views"])


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="blog_comments"
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies"
    )

    is_approved = models.BooleanField(default=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.author.username} on {self.post.title}"

    @property
    def is_reply(self):
        return self.parent is not None
