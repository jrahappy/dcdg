#!/bin/bash
# Quick fix script for AWS - run this on your server

echo "=== Quick AWS CSRF Fix ==="
echo ""
echo "Creating .env file with your server settings..."

# Get the server IP
SERVER_IP="54.208.189.63"
echo "Using server IP: $SERVER_IP"

# Create .env file
cat > .env << EOF
# Django Settings
DEBUG=False
SECRET_KEY=your-secret-key-change-this-immediately

# Allowed Hosts
ALLOWED_HOSTS=$SERVER_IP,localhost,127.0.0.1

# CSRF Settings - IMPORTANT!
CSRF_TRUSTED_ORIGINS=http://$SERVER_IP:8000,http://$SERVER_IP

# Cookie Security (False for HTTP)
CSRF_COOKIE_SECURE=False
SESSION_COOKIE_SECURE=False

# Database
DATABASE_URL=sqlite:///db.sqlite3

# Static/Media
STATIC_ROOT=staticfiles
MEDIA_ROOT=media
EOF

echo ".env file created!"
echo ""
echo "Now run these commands:"
echo "1. python manage.py collectstatic --noinput"
echo "2. Restart your server:"
echo "   python manage.py runserver 0.0.0.0:8000"
echo ""
echo "3. Clear your browser cache and try again!"