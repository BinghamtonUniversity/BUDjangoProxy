from django.http import request, JsonResponse
from ..models import API, APIInstance, APIDeveloper, ActivityLog

def can_get_activity_logs(request):
    return request.user.admin
