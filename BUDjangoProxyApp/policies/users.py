from django.http import request, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from ..models import User, APIDeveloper

def can_get_create_users(request):
   return request.user.admin

def can_manage_user(request,id):
    try:
        user = User.objects.get(id=id)
    except User.DoesNotExist:
        user = None

    if request.method == 'DELETE':
        if request.user.admin:
            return True, user
        else:
            return False, JsonResponse({"error": "Not authorized to manage this API"}, status=403)

    return request.user.admin, user