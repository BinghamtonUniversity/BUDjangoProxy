from django.http import request, JsonResponse
from ..models import Environment, APIDeveloper


def can_get_create_environment(request):
    if request.method == "GET":
        is_api_developer = APIDeveloper.objects.filter(api_developer=request.user).exists()
        return request.user.admin or request.user.developer or is_api_developer

    if request.user.admin:
        return True
    else:
        return False

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