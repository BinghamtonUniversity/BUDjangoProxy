from django.http import request, JsonResponse
from ..models import API, APIDeveloper, APIVersion, APIInstance


def can_get_create_apis(request):
    if request.method == "GET":
        is_api_developer = APIDeveloper.objects.filter(api_developer=request.user.id).exists()
        return request.user.admin or request.user.developer or is_api_developer
    else:
        if request.user.admin or request.user.developer:
            return True
        else:
            return False

def can_manage_api(request,id):
    try:
        api = API.objects.get(id=id)
    except API.DoesNotExist:
        api = None

    if request.method == 'DELETE':
        if request.user.admin or api.user.unique_id == request.user.unique_id:
            return True, api
        else:
            return False, JsonResponse({"error": "Not authorized to manage this API"}, status=403)

    try:
        is_api_developer = APIDeveloper.objects.filter(api_developer=request.user.id, api=api.id).exists()
    except APIDeveloper.DoesNotExist:
        return False, JsonResponse({"error": "Not authorized to manage this API"}, status=403)

    return is_api_developer or api.user.unique_id == request.user.unique_id, api

def can_manage_api_version(request,id):
    try:
        api = API.objects.get(id=id)
    except API.DoesNotExist:
        api = None

    if request.method == 'DELETE':
        if request.user.admin or api.user.unique_id == request.user.unique_id:
            return True, api
        else:
            return False, JsonResponse({"error": "Not authorized to manage this API"}, status=403)

    try:
        is_api_developer = APIDeveloper.objects.filter(api_developer=request.user.id, api=api.id).exists()
    except APIDeveloper.DoesNotExist:
        return False, JsonResponse({"error": "Not authorized to manage this API"}, status=403)

    return is_api_developer or api.user.unique_id == request.user.unique_id, api

