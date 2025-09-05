from django.http import request, JsonResponse
from ..models import API, APIInstance, APIDeveloper

def can_get_create_api_instance(request):
    if request.method == "GET":
        is_api_developer = APIDeveloper.objects.filter(user=request.user).exists()
        return request.user.admin or request.user.developer or is_api_developer

    if request.user.admin:
        return True
    else:
        return False

def can_manage_api_instance(request,id):
    try:
        api_instance = APIInstance.objects.get(id=id)
    except API.DoesNotExist:
        api_instance = None

    if request.method == 'DELETE':
        if request.user.admin or api_instance.api.user.unique_id == request.user.unique_id:
            return True, api_instance
        else:
            return False, JsonResponse({"error": "Not authorized to manage this API"}, status=403)

    try:
        is_api_developer = APIDeveloper.objects.filter(api_developer=request.user.id, api=api_instance.api.id).exists()
    except APIDeveloper.DoesNotExist:
        return False, JsonResponse({"error": "Not authorized to manage this API"}, status=403)

    return is_api_developer or api_instance.api.user.unique_id == request.user.unique_id, api_instance
