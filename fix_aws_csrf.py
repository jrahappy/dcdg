#!/usr/bin/env python
"""
Quick fix script for AWS CSRF issues
Run this on your AWS server to diagnose and fix CSRF problems
"""

import os
import sys

def check_settings():
    """Check current Django settings"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    import django
    django.setup()
    
    from django.conf import settings
    
    print("=== Current Django Settings ===")
    print(f"DEBUG: {settings.DEBUG}")
    print(f"ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
    print(f"CSRF_TRUSTED_ORIGINS: {getattr(settings, 'CSRF_TRUSTED_ORIGINS', 'Not set')}")
    print(f"CSRF_COOKIE_SECURE: {getattr(settings, 'CSRF_COOKIE_SECURE', 'Not set')}")
    print(f"SESSION_COOKIE_SECURE: {getattr(settings, 'SESSION_COOKIE_SECURE', 'Not set')}")
    print(f"CSRF_COOKIE_HTTPONLY: {getattr(settings, 'CSRF_COOKIE_HTTPONLY', 'Not set')}")
    print()

def create_env_file():
    """Create or update .env file with proper settings"""
    print("=== Creating/Updating .env file ===")
    
    # Get server info
    server_ip = input("Enter your server IP address (e.g., 54.208.189.63): ").strip()
    domain = input("Enter your domain name (if any, press Enter to skip): ").strip()
    use_https = input("Are you using HTTPS? (y/n): ").strip().lower() == 'y'
    
    # Build configuration
    allowed_hosts = [server_ip]
    csrf_origins = []
    
    if domain:
        allowed_hosts.append(domain)
        allowed_hosts.append(f"www.{domain}")
        scheme = "https" if use_https else "http"
        csrf_origins.append(f"{scheme}://{domain}")
        csrf_origins.append(f"{scheme}://www.{domain}")
    
    # Add IP with port
    csrf_origins.append(f"http://{server_ip}:8000")
    csrf_origins.append(f"http://{server_ip}")
    
    # Create .env content
    env_content = f"""# Django Settings
DEBUG=False
SECRET_KEY=your-secret-key-here

# Allowed Hosts
ALLOWED_HOSTS={','.join(allowed_hosts)}

# CSRF Settings
CSRF_TRUSTED_ORIGINS={','.join(csrf_origins)}

# Cookie Security (set to False if not using HTTPS)
CSRF_COOKIE_SECURE={'True' if use_https else 'False'}
SESSION_COOKIE_SECURE={'True' if use_https else 'False'}

# Database (update as needed)
DATABASE_URL=sqlite:///db.sqlite3
"""
    
    # Check if .env exists
    if os.path.exists('.env'):
        backup = input(".env file exists. Create backup? (y/n): ").strip().lower()
        if backup == 'y':
            import shutil
            shutil.copy('.env', '.env.backup')
            print("Backup created: .env.backup")
    
    # Write new .env
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print(".env file created/updated successfully!")
    print("\nPlease update the SECRET_KEY and DATABASE_URL as needed.")
    return server_ip

def test_csrf_setup(server_ip):
    """Test if CSRF is properly configured"""
    print("\n=== Testing CSRF Setup ===")
    
    # Re-check settings after .env update
    os.environ.clear()
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    
    # Force reload of settings
    from importlib import reload
    import django.conf
    reload(django.conf)
    
    import django
    django.setup()
    from django.conf import settings
    
    print("After .env update:")
    print(f"ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
    print(f"CSRF_TRUSTED_ORIGINS: {getattr(settings, 'CSRF_TRUSTED_ORIGINS', 'Not set')}")
    
    # Test instructions
    print("\n=== Next Steps ===")
    print("1. Restart your Django application:")
    print("   - If using development server: python manage.py runserver 0.0.0.0:8000")
    print("   - If using Gunicorn: sudo systemctl restart gunicorn")
    print("   - If using supervisor: sudo supervisorctl restart your-app")
    print()
    print("2. Clear your browser cache and cookies")
    print()
    print("3. Test the Add to Cart button")
    print()
    print("4. If still not working, check:")
    print(f"   - Browser DevTools > Network > Check the POST request to /cart/add/")
    print(f"   - Look for X-CSRFToken header in request")
    print(f"   - Look for csrftoken in cookies")
    print()
    print("5. You can also temporarily test with DEBUG=True in .env to see detailed errors")

def main():
    print("=== AWS CSRF Fix Script ===\n")
    
    # Check current settings
    try:
        check_settings()
    except Exception as e:
        print(f"Error checking settings: {e}")
        print("Continuing with .env creation...\n")
    
    # Ask user what to do
    action = input("Do you want to create/update .env file? (y/n): ").strip().lower()
    
    if action == 'y':
        server_ip = create_env_file()
        test_csrf_setup(server_ip)
    else:
        print("\nManual configuration needed:")
        print("Add to your .env or settings.py:")
        print("ALLOWED_HOSTS=your-server-ip,your-domain")
        print("CSRF_TRUSTED_ORIGINS=http://your-server-ip:8000,https://your-domain")

if __name__ == "__main__":
    main()