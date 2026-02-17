from django.http import request, JsonResponse
from ..models import API, APIInstance, APIDeveloper, ActivityLog

def can_get_activity_logs(request):
    if request.method == "GET":
        is_api_developer = APIDeveloper.objects.filter(user_id=request.user).exists()
        return request.user.admin or request.user.developer or is_api_developer

    if request.user.active and (request.user.admin or request.user.developer):
        return True
    else:
        return False
