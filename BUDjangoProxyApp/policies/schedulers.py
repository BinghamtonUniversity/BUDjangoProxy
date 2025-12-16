from django.http import request, JsonResponse
from ..models import  APIDeveloper, Scheduler

def can_get_create_scheduler(request):
    if request.method == "GET":
        is_api_developer = APIDeveloper.objects.filter(api_developer=request.user).exists()
        return request.user.admin or request.user.developer or is_api_developer

    if request.user.active and (request.user.admin or request.user.developer):
        return True
    else:
        return False

def can_manage_scheduler(request,id):
    try:
        scheduler = Scheduler.objects.get(id=id)
    except Scheduler.DoesNotExist:
        scheduler = None

    if request.method == 'DELETE' or request.method == 'PUT':
        if request.user.admin or request.user.developer:
            return True, scheduler
        else:
            return False, JsonResponse({"error": "Not authorized to manage the schedule"}, status=403)

    return request.user.admin or request.user.developer
