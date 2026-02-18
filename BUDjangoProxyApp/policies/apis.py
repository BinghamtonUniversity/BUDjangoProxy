from django.http import request, JsonResponse
from ..models import API, APIDeveloper, APIVersion, APIInstance


def can_get_create_apis(request):
    if request.method == "GET":
        is_api_developer = APIDeveloper.objects.filter(user_id=request.user.id).exists()
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
        is_api_developer = APIDeveloper.objects.filter(user_id=request.user.id, api=api.id).exists()
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
        is_api_developer = APIDeveloper.objects.filter(user_id=request.user.id, api=api.id).exists()
    except APIDeveloper.DoesNotExist:
        return False, JsonResponse({"error": "Not authorized to manage this API"}, status=403)

    return is_api_developer or api.user.unique_id == request.user.unique_id, api


def can_get_create_api_developers(request, api_id):
    try:
        api = API.objects.get(id=api_id)
    except API.DoesNotExist:
        return False, JsonResponse({"error": "API Doesn't Exist"}, status=403)

    is_api_developer = APIDeveloper.objects.filter(user_id=request.user.id, api=api_id).exists()

    if request.method == "GET":
        return is_api_developer or request.user.admin or request.user.developer or api.user.unique_id == request.user.unique_id, api

    elif request.method == 'POST':
        if is_api_developer or request.user.admin or api.user.unique_id == request.user.unique_id:
            return True, api

def can_manage_api_developers(request,api_id):
    try:
        api = API.objects.get(id=api_id)
    except API.DoesNotExist:
        return False, JsonResponse({"error": "API Doesn't Exist"}, status=403)

    if request.method == 'DELETE' or request.method == 'POST':
        if request.user.admin or api.user.unique_id == request.user.unique_id:
            return True, api
