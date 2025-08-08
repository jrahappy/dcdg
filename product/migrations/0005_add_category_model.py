# Manual migration for adding Category model and converting Product category field
from django.db import migrations, models
import django.db.models.deletion


def create_categories_from_products(apps, schema_editor):
    """Create Category instances from existing product categories"""
    Category = apps.get_model('product', 'Category')
    Product = apps.get_model('product', 'Product')
    
    # Category mapping
    category_mapping = {
        "equipment": "Equipment",
        "supplies": "Supplies",
        "instruments": "Instruments",
        "materials": "Materials",
        "software": "Software",
        "services": "Services",
        "other": "Other",
    }
    
    # Create categories
    categories = {}
    for key, name in category_mapping.items():
        category = Category.objects.create(
            name=name,
            slug=key,
            is_active=True
        )
        categories[key] = category
    
    # Update products with new categories
    for product in Product.objects.all():
        if hasattr(product, 'category_old') and product.category_old:
            product.category_new = categories.get(product.category_old)
            product.save()


def reverse_categories(apps, schema_editor):
    """Reverse the category conversion"""
    Product = apps.get_model('product', 'Product')
    
    # Revert products to old category values
    for product in Product.objects.all():
        if product.category_new:
            product.category_old = product.category_new.slug
            product.save()


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0004_alter_product_sku'),
    ]

    operations = [
        # Create Category model
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('slug', models.SlugField(blank=True, max_length=120, unique=True)),
                ('description', models.TextField(blank=True)),
                ('icon', models.CharField(blank=True, help_text='Icon class name (e.g., fas fa-tooth)', max_length=50)),
                ('is_active', models.BooleanField(default=True)),
                ('order', models.IntegerField(default=0, help_text='Display order')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='product.category')),
            ],
            options={
                'verbose_name': 'Category',
                'verbose_name_plural': 'Categories',
                'ordering': ['order', 'name'],
            },
        ),
        
        # Add unique_together constraint
        migrations.AlterUniqueTogether(
            name='category',
            unique_together={('parent', 'slug')},
        ),
        
        # Rename existing category field to category_old
        migrations.RenameField(
            model_name='product',
            old_name='category',
            new_name='category_old',
        ),
        
        # Add new category_new field
        migrations.AddField(
            model_name='product',
            name='category_new',
            field=models.ForeignKey(blank=True, help_text='Product category', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='products', to='product.category'),
        ),
        
        # Remove old index
        migrations.RemoveIndex(
            model_name='product',
            name='product_pro_status_42a9a9_idx',
        ),
        
        # Run data migration
        migrations.RunPython(create_categories_from_products, reverse_categories),
        
        # Remove old field
        migrations.RemoveField(
            model_name='product',
            name='category_old',
        ),
        
        # Rename new field to category
        migrations.RenameField(
            model_name='product',
            old_name='category_new',
            new_name='category',
        ),
        
        # Add new indexes
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['status'], name='product_pro_status_48d769_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['category'], name='product_pro_categor_2b9d78_idx'),
        ),
    ]