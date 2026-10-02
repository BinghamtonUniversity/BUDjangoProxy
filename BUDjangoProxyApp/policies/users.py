from django.http import request, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from ..models import User, APIDeveloper

def can_get_create_users(request):
   if request.method == 'POST':
       return request.user.admin
   is_api_developer = APIDeveloper.objects.filter(user_id=request.user).exists()
   return request.user.active and (request.user.admin or request.user.developer or is_api_developer)

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