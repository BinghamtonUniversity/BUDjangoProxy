from django.http import request, JsonResponse
from ..models import Resource, APIDeveloper

def can_get_create_resource(request):
    if request.method == "GET":
        is_api_developer = APIDeveloper.objects.filter(api_developer=request.user).exists()
        return request.user.admin or request.user.developer or is_api_developer
    else:
        if request.user.admin:
            return True
        else:
            return False


def can_manage_resource(request,id):
    try:
        resource = Resource.objects.get(id=id)
    except Resource.DoesNotExist:
        resource = None

    if request.method == 'DELETE':
        if request.user.admin:
            return True, resource
        else:
            return False, JsonResponse({"error": "Not authorized to manage the resources"}, status=403)

    return request.user.admin or request.user.developer, resource