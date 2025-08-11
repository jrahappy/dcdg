# AWS Deployment Fix for Add to Cart 403 Forbidden Error

## Problem
The "Add to Cart" button returns a 403 Forbidden error on AWS Ubuntu server due to CSRF token validation issues.

## Solution Steps

### 1. Update Environment Variables (.env file on AWS server)

Add these to your `.env` file on the AWS server:

```bash
# Replace with your actual domain/IP
ALLOWED_HOSTS=your-domain.com,www.your-domain.com,your-server-ip
CSRF_TRUSTED_ORIGINS=https://your-domain.com,https://www.your-domain.com,http://your-server-ip

# If using HTTP (not HTTPS), set these to False
CSRF_COOKIE_SECURE=False
SESSION_COOKIE_SECURE=False

# Ensure DEBUG is False in production
DEBUG=False
```

### 2. If Using Nginx, Update Nginx Configuration

Edit your nginx site configuration (usually in `/etc/nginx/sites-available/your-site`):

```nginx
server {
    # ... other configuration ...

    location / {
        proxy_pass http://127.0.0.1:8000;  # or your gunicorn socket
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        
        # Important headers for CSRF
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $server_name;
    }
    
    # ... rest of configuration ...
}
```

### 3. Update Django Settings (if not using .env)

If you're not using environment variables, directly update `core/settings.py`:

```python
# Replace with your actual domain/IP
ALLOWED_HOSTS = ['your-domain.com', 'www.your-domain.com', 'your-server-ip']

CSRF_TRUSTED_ORIGINS = [
    'https://your-domain.com',
    'https://www.your-domain.com',
    'http://your-server-ip:8000',  # Include port if not using 80/443
]

# Only if using HTTPS
CSRF_COOKIE_SECURE = True  # Set to False if using HTTP
SESSION_COOKIE_SECURE = True  # Set to False if using HTTP

# Ensure CSRF cookie is accessible by JavaScript
CSRF_COOKIE_HTTPONLY = False
```

### 4. Collect Static Files

```bash
cd /path/to/your/project
source venv/bin/activate
python manage.py collectstatic --noinput
```

### 5. Restart Services

```bash
# If using Gunicorn
sudo systemctl restart gunicorn

# If using Nginx
sudo systemctl restart nginx

# Or if running development server
# Kill existing process
pkill -f "python manage.py runserver"
# Start again
python manage.py runserver 0.0.0.0:8000
```

### 6. Clear Browser Cache

1. Clear browser cookies and cache for your domain
2. Try in incognito/private mode first
3. Check browser console for any remaining errors

### 7. Debug Checklist

If still not working, check:

```bash
# Check Django is receiving correct host headers
python manage.py shell
>>> from django.conf import settings
>>> print(settings.ALLOWED_HOSTS)
>>> print(settings.CSRF_TRUSTED_ORIGINS)

# Check if CSRF token is being set
# In browser DevTools > Application > Cookies
# Look for 'csrftoken' cookie

# Check Django logs
tail -f /var/log/your-app/django.log

# Check Nginx error logs
sudo tail -f /var/log/nginx/error.log
```

### 8. Alternative: Temporary Debug Mode

For testing only (NOT for production):

```python
# In views.py, temporarily add to debug
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt  # Remove this after debugging!
def add_to_cart(request, pk):
    # ... rest of the view
```

### 9. Common Issues and Solutions

**Issue: Cookie not being set**
- Solution: Check domain settings match exactly
- Ensure not mixing HTTP/HTTPS

**Issue: Token present but still 403**
- Solution: Check CSRF_TRUSTED_ORIGINS includes your exact domain with scheme

**Issue: Works locally but not on server**
- Solution: Usually proxy headers issue - ensure Nginx forwards headers correctly

## Testing

After applying fixes, test:

1. Open browser DevTools Network tab
2. Click "Add to Cart"
3. Check request headers for:
   - X-CSRFToken header
   - Cookie header with csrftoken
4. Check response for specific error message

## Security Note

Never disable CSRF protection in production. Always fix the root cause instead of bypassing security.