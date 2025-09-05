from django.http import JsonResponse, HttpResponseNotAllowed
from django.utils.translation.trans_null import activate

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

        # if
        if not auth_header or not auth_header.startswith('Basic '):
            return self.prompt_for_credentials()

        try:
            # Decode credentials
            auth_data = base64.b64decode(auth_header.split(' ')[1]).decode('utf-8')
            print(auth_data)
            root_api_user, root_api_password = auth_data.split(':', 1)
        except (IndexError, ValueError, base64.binascii.Error):
            return JsonResponse({'error': 'Invalid authorization header'}, status=401)

        if not (unique_id and root_api_user and root_api_password):
            return JsonResponse({"error": "Missing authentication headers"}, status=401)

        try:
            current_user = User.objects.get(unique_id=unique_id)
            request.user = current_user
            # Check whether the user is active or not
            if not current_user.active:
                return JsonResponse({"error": "Unauthorized developer"}, status=403)
        except User.DoesNotExist:

            # current_user = User(unique_id=unique_id, active=True, admin=False, developer=False)
            # current_user.save()

            return JsonResponse({"error": "Unauthorized developer"}, status=403)


        # # Admin auth
        # if root_api_user == self.root_api_user and root_api_password == self.root_api_password:
        #     request.admin = current_user.admin
        #     request.developer = current_user.developer

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
