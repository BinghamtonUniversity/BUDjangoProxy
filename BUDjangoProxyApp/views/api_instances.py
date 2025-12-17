from django.forms import model_to_dict
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, JsonResponse, HttpRequest, HttpResponseNotFound
from django.views.decorators.csrf import csrf_exempt
from sqlparse.utils import recurse
from BUDjangoProxyApp.lib.helpers import instance_to_dict
from ..models import *
from ..lib.policies_wrapper import policy
from ..policies.api_instances import *
import os
import shutil
import BUDjangoProxy.settings as settings

@csrf_exempt
@policy(can_get_create_api_instance)
def get_create_api_instances(request):
    if request.method not in ['GET', 'POST']:
        return JsonResponse({"error":"Method not allowed"}, status=405)

    if request.method == 'GET':
        return JsonResponse(list(APIInstance.objects.all().values("id", "name","route",
                                                                  "api_id","api_version_id",
                                                                  "environment_id","resources",
                                                                  "options","route_user_map",
                                                                  "public", "errors",
                                                                  "created_at", "updated_at"
        )
                                 ), safe=False)
    elif request.method == 'POST':
        try:
            api_instance = APIInstance(**request.data)
            api_instance.save()
            response_data = instance_to_dict(api_instance, ['api', 'environment', 'api_version'])

            return JsonResponse(response_data, safe=False)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@policy(can_manage_api_instance,object_arg_name='id')
def get_manage_api_instance(request, id):
    if request.method not in ['GET', 'PUT','DELETE']:
        return JsonResponse({"error":"Method not allowed"}, status=405)

    if request.method == 'GET':
        request_data = APIInstance.objects.get(id=id)
        response_data = instance_to_dict(request_data, ['api', 'environment', 'api_version'])

        return JsonResponse(response_data,safe=False)
    elif request.method == 'PUT':
        # try:
        request_data = request.data
        api_instance = APIInstance.objects.filter(id=id).first()
        api_instance.name = request_data['name']
        api_instance.route = request_data['route']
        api_instance.route_user_map = request_data['route_user_map']
        api_instance.api_version_id = request_data['api_version_id'] if 'api_version_id' in request_data and request_data['api_version_id'] else None
        api_instance.resources = request_data['resources']
        api_instance.options = request_data['options']
        api_instance.public = request_data['public']
        api_instance.save()

        response_data = instance_to_dict(APIInstance.objects.get(id=id), ['api', 'environment', 'api_version'])

        return JsonResponse(response_data, safe=False)
        # except Exception as e:
        #     return JsonResponse({"error": str(e)}, status=500)
    elif request.method == 'DELETE':
        try:
            APIInstance.objects.filter(id=id).delete()

            # Deleting the files/folders for that instance under dynamic_apps directory
            instance_folder = os.path.join(settings.BASE_DIR, "BUDjangoProxyApp", "dynamic_apps",f"{id}")
            shutil.rmtree(instance_folder)

            return JsonResponse({'message': "Success"}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


