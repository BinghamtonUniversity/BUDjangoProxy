from django.http import request, JsonResponse
from ..models import APIDeveloper, APIUser


def can_get_create_api_user(request):
    if request.method == "GET":
        is_api_developer = APIDeveloper.objects.filter(api_developer=request.user).exists()
        return request.user.admin or request.user.developer or is_api_developer

    if request.user.admin:
        return True
    else:
        return False


def can_manage_api_user(request, id):
    try:
        api_user = APIUser.objects.get(id=id)
    except APIUser.DoesNotExist:
        api_user = None

    if request.method == 'DELETE':
        if request.user.admin:
            return True, api_user
        else:
            return False, JsonResponse({"error": "Not authorized to manage environments"}, status=403)

    return request.user.admin or request.user.developer, api_user