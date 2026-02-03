from django.http import JsonResponse, HttpResponseNotAllowed
from django.utils.deprecation import MiddlewareMixin
from .request_context import set_request_user_info, set_request_context

from BUDjangoProxyApp.models import User, APIDeveloper
import base64

from dotenv import dotenv_values
env_values = dotenv_values(".env")

class UserAuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.root_api_user = env_values["API_USER"]
        self.root_api_password = env_values["API_PASSWORD"]

    def __call__(self, request):
        unique_id = request.headers.get("X-Unique-Id")
        if not unique_id:
            return JsonResponse({"error": "Missing authentication headers"}, status=401)

        auth_header = request.META.get('HTTP_AUTHORIZATION')

        if not auth_header or not auth_header.startswith('Basic '):
            return self.prompt_for_credentials()

        try:
            # Decode credentials
            auth_data = base64.b64decode(auth_header.split(' ')[1]).decode('utf-8')
            root_api_user, root_api_password = auth_data.split(':', 1)
        except (IndexError, ValueError, base64.binascii.Error):
            return JsonResponse({'error': 'Invalid authorization header'}, status=401)

        if not (unique_id and root_api_user and root_api_password):
            return JsonResponse({"error": "Missing authentication headers"}, status=401)

        try:
            if root_api_user != self.root_api_user and root_api_password != self.root_api_password:
                return JsonResponse({"error": "Unauthorized"}, status=403)

            current_user = User.objects.get(unique_id=unique_id)
            request.user = current_user
            # Check whether the user is active or not
            if not current_user.active:
                return JsonResponse({"error": "Unauthorized developer"}, status=403)
        except User.DoesNotExist:
            return JsonResponse({"error": "Unauthorized developer"}, status=403)

        set_request_user_info(current_user)
        return self.get_response(request)

    @staticmethod
    def prompt_for_credentials():
        """
        Returns a response prompting for Basic Authentication credentials.
        """
        return JsonResponse(
            {'error': 'Unauthorized'},
            status=401,
            headers={'WWW-Authenticate': 'Basic realm="API"'}
        )

class NoCacheAuthMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response["Pragma"] = "no-cache"
        response["Expires"] = "0"
        return response


class RequestContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        set_request_context(request)
        return self.get_response(request)