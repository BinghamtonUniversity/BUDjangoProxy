from django.http import request, JsonResponse
from ..models import Environment, APIDeveloper, API


def can_get_create_environment(request):
    if request.method == "GET":
        is_api_developer = APIDeveloper.objects.filter(user_id=request.user).exists()
        is_api_owner = API.objects.filter(user_id=request.user).exists()
        return request.user.admin or request.user.developer or is_api_developer or is_api_owner
    return request.user.admin

def can_manage_environment(request,id):
    try:
        environment = Environment.objects.get(id=id)
    except Environment.DoesNotExist:
        environment = None

    if request.method == 'DELETE':
        if request.user.admin:
            return True, environment
        else:
            return False, JsonResponse({"error": "Not authorized to manage environments"}, status=403)

    return request.user.admin, environment