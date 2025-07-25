from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Fix usernames for users who only have emails'

    def handle(self, *args, **options):
        users = User.objects.all()
        
        for user in users:
            if not user.username or user.username == user.email:
                # Generate a username from email
                username_base = user.email.split('@')[0]
                username = username_base
                counter = 1
                
                # Ensure username is unique
                while User.objects.filter(username=username).exclude(pk=user.pk).exists():
                    username = f"{username_base}{counter}"
                    counter += 1
                
                user.username = username
                user.save()
                self.stdout.write(self.style.SUCCESS(f'Updated username for {user.email} to {username}'))
            else:
                self.stdout.write(f'User {user.email} already has username: {user.username}')