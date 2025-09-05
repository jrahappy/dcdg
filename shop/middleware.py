from django.utils.deprecation import MiddlewareMixin
import logging

logger = logging.getLogger(__name__)


class PreserveCartSessionMiddleware(MiddlewareMixin):
    """
    Middleware to preserve the session key before login
    so that the cart can be properly migrated.
    """
    
    def process_request(self, request):
        """
        Store the current session key before it potentially gets cycled during login.
        This runs before Django's authentication backend processes the login.
        """
        if request.method == 'POST' and 'login' in request.path:
            # Check if we have a session key before login
            if hasattr(request, 'session') and request.session.session_key:
                # Store the pre-login session key
                request.session['_old_session_key'] = request.session.session_key
                request.session.save()
                logger.debug(f"Stored pre-login session key: {request.session.session_key[:8]}...")
        
        return None
    
    def process_response(self, request, response):
        """
        Clean up the old session key after successful cart migration.
        """
        if hasattr(request, 'session') and '_old_session_key' in request.session:
            # Only clean up if user is now authenticated (login was successful)
            if hasattr(request, 'user') and request.user.is_authenticated:
                # Give the signal handler time to process
                # We'll clean this up on the next request
                pass
        
        return response