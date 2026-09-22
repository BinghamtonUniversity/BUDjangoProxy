from django.http import request, JsonResponse
from ..models import APIDeveloper, APIUser


def can_get_create_api_user(request):
    if request.method == "GET":
        is_api_developer = APIDeveloper.objects.filter(user_id=request.user).exists()
        return request.user.admin or request.user.developer or is_api_developer

    if request.user.admin:
        return True
    else:
        return False


def can_manage_api_user(request):
    return request.user.admin or request.user.developer

def can_see_secret(request):
    if request.method != "GET":
        return False

    return request.user.admin or request.user.developer