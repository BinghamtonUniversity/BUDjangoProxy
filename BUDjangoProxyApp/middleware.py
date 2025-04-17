from django.http import JsonResponse
from .models import APIInstance, APIUser, Environment
from .services.CustomPathResolver import CustomPathResolver
from .services.VersionControl import VersionControl
from .services.dynamic_loader import DynamicAppManager
import base64

class DynamicRoutingMiddleware:
    EXCLUDED_PATHS = ['/admin/', '/static/','/api/']  # Routes to be excluded from dynamic routing

    def __init__(self, get_response):
        self.get_response = get_response
        DynamicAppManager.reload_all_instances()

    def __call__(self, request):
        if any(request.path.startswith(path) for path in self.EXCLUDED_PATHS):
            return self.get_response(request)

        # Extract path and validate format
        path = request.path.strip('/').split('/')
        if len(path) < 2:
            return JsonResponse({'error': 'Invalid route format'}, status=400)

        app_route, view_path = path[0], path[1]

        # Retrieve subdomain and environment
        domain = request.get_host().split(':')[0]
        try:
            environment = Environment.objects.get(domain=domain)
        except Environment.DoesNotExist:
            return JsonResponse({'error': 'Environment not found'}, status=404)

        # Retrieve API instance
        try:
            api_instance = APIInstance.objects.get(route=app_route, environment=environment)
        except APIInstance.DoesNotExist:
            return JsonResponse({'error': 'API instance not found'}, status=404)

        # Authenticate API user for every request
        api_user = self.authenticate_api_user(request, api_instance)
        if isinstance(api_user, JsonResponse):  # Authentication failed
            return api_user

        # Attach authenticated user and API instance to the request
        request.api_user = api_user
        request.api_instance = api_instance
        # print(request.__contains__)

        version_control = VersionControl()
        if not version_control.file_integrity_check(api_instance):
            DynamicAppManager.load_api_instance(api_instance)

        custom_resolver = CustomPathResolver()

        custom_resolver.incoming_url_fix(request, api_instance)
        view_func, args, kwargs = custom_resolver.resolve(request, api_instance)


        # Dynamically load and execute the view
        view_func = DynamicAppManager.get_view(request.api_instance, view_func.__name__)
        return view_func(request, *args, **kwargs)

    def authenticate_api_user(self, request, api_instance):
        """
        Authenticates the API user using Basic Authentication and verifies access to the API instance.
        This happens on every request to ensure stateless behavior.
        """
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header or not auth_header.startswith('Basic '):
            return self.prompt_for_credentials()

        try:
            # Decode credentials
            auth_data = base64.b64decode(auth_header.split(' ')[1]).decode('utf-8')
            username, password = auth_data.split(':', 1)
        except (IndexError, ValueError, base64.binascii.Error):
            return JsonResponse({'error': 'Invalid authorization header'}, status=401)

        try:
            # Retrieve and authenticate the user
            api_user = APIUser.objects.get(app_name=username)
            if not api_user.check_password(password):
                raise APIUser.DoesNotExist
            if not api_user.is_active:
                return JsonResponse({'error': 'User account is inactive'}, status=403)

            request_user = next((e for e in api_instance.route_user_map if int(e['api_user']) == api_user.id), None)

            if request_user is None:
                return self.prompt_for_credentials()
            if request_user['verb'] != "ALL" and request_user['verb'] != request.method:
                return self.prompt_for_credentials()

            print("found user!")
        except APIUser.DoesNotExist:
            return self.prompt_for_credentials()

        # Verify user access to the specific API instance
        # if api_instance not in api_user.api_instances.all():

        return api_user

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


# middleware.py
# import json
# from django.http import HttpRequest
# from django.core.exceptions import SuspiciousOperation
#
# class NormalizeRequestDataMiddleware:
#     def __init__(self, get_response):
#         self.get_response = get_response
#
#     def __call__(self, request: HttpRequest):
#         # Start with GET and POST data
#         # Initialize an empty dictionary for all request data
#         all_data = {}
#
#         # Add GET parameters
#         all_data.update(request.GET.items())
#
#         # Handle POST data (form data or urlencoded)
#         if request.method in ['POST', 'PUT']:
#             # Include POST data (works for application/x-www-form-urlencoded)
#             all_data.update(request.POST.items())
#
#             # Include files if present (multipart/form-data)
#             if request.FILES:
#                 files_data = {key: value.name for key, value in request.FILES.items()}
#                 all_data.update({'files': files_data})  # Add file names as a sub-dictionary
#
#             # Handle JSON if content type is application/json
#             if request.content_type == 'application/json':
#                 try:
#                     json_data = json.loads(request.body.decode('utf-8'))
#                     all_data.update(json_data)
#                 except (json.JSONDecodeError, UnicodeDecodeError):
#                     pass  # Fallback to existing data
#         request.data = all_data
#         return request