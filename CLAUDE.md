# CLAUDE.md - Project Context for Django Dental Support Organization

## Project Overview
Django-based dental support organization system with ongoing Tailwind CSS conversion.

## Recent Work (Last updated: 2025-07-26)

### Completed Tasks
1. **Removed checkboxes from list views**
   - Customer list (`dashboard/templates/dashboard/customer_list.html`)
   - Blog list (`dashboard/templates/dashboard/blog_list.html`)
   - Campaign list (`email_campaign/templates/email_campaign/campaign_list.html`)
   - Target Groups list (`email_campaign/templates/email_campaign/target_group_list.html`)

2. **Added Sender Information Feature**
   - Location: Account Management menu
   - Models: `SenderInformation`, `SenderEmail` in `accounts/models.py`
   - View: `sender_information` in `accounts/views.py`
   - Template: `templates/accounts/sender_information.html`
   - Features:
     - Business information management (name, address, phone, website)
     - Multiple email addresses with SMTP configuration
     - Email verification via SMTP test
     - Modal-based configuration UI
     - Primary email selection

3. **Fixed Target Group Cart Page**
   - Converted `email_campaign/templates/email_campaign/target_group_cart.html` to Tailwind CSS
   - Removed old custom CSS styles
   - Fixed styling errors

### Pending Tasks (from TODO list)
1. Convert Blog templates to Tailwind CSS
2. Convert remaining Campaign templates to Tailwind CSS
3. Convert Target Group templates to Tailwind CSS
4. Convert Dashboard base template to Tailwind CSS

### Technical Stack
- Django 5.2.4
- Tailwind CSS v4
- PostgreSQL database
- Django Allauth for authentication
- Vite for asset bundling

### Important Commands
```bash
# Run development server
python manage.py runserver

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Tailwind CSS (if needed)
npm run dev
```

### Known Issues/Notes
- All list views now have checkboxes removed
- Sender Information is fully functional with modal-based SMTP configuration
- Target group cart page is now using Tailwind CSS

### Next Steps
Continue with Tailwind CSS conversion for remaining templates, focusing on:
- Blog post creation/editing forms
- Campaign detail views
- Target group management pages