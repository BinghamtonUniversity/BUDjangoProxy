from django.forms import model_to_dict
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, JsonResponse, HttpRequest, HttpResponseNotFound
from django.views.decorators.csrf import csrf_exempt
from ..models import *
from ..lib.policies_wrapper import policy
from ..policies.resources import *

@csrf_exempt
@policy(can_get_create_resource)
def get_create_resources(request):
    if request.method not in ['GET','POST']:
        return JsonResponse({"error":"Method not allowed"}, status=405)

    if request.method == 'GET':
        return JsonResponse(list(Resource.objects.all().values()), safe=False)
    elif request.method == 'POST':
        try:
            resource = Resource(**request.data)
            if resource.resource_type == 'secret':
                resource.config['value'] = LaravelEncryptor().encrypt(resource.config['value'])
            elif resource.resource_type == 'oracle' or resource.resource_type == 'mysql' or resource.resource_type == 'sqlsrv':
                resource.config['pass'] = LaravelEncryptor().encrypt(resource.config['pass'])

            resource.save()
            return JsonResponse(model_to_dict(resource), safe=False)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@policy(can_manage_resource,object_arg_name='id')
def get_manage_resource(request, id):
    if request.method not in ['GET','PUT','DELETE']:
        return JsonResponse({"error":"Method not allowed"}, status=405)

    if request.method == 'GET':
        request_data = get_object_or_404(Resource, id=id)
        return JsonResponse(model_to_dict(request_data),safe=False)
    elif request.method == 'PUT':
        try:
            request_data = request.data
            if request_data['resource_type'] == 'secret':
                request_data['config']['value'] = LaravelEncryptor().encrypt(request_data['config']['value'])
            elif request_data['resource_type'] == 'oracle' or request_data['resource_type'] == 'mysql' or request_data['resource_type'] == 'sqlsrv':
                request_data['config']['pass'] = LaravelEncryptor().encrypt(request_data['config']['pass'])

            Resource.objects.filter(id=id).update(**request_data)
            return JsonResponse(model_to_dict(Resource.objects.get(id=id)), safe=False)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    elif request.method == 'DELETE':
        Resource.objects.filter(id=id).delete()
        return JsonResponse({'message': "Success"}, safe=False)

@csrf_exempt
@policy(can_get_create_resource)
def get_resources_by_type(request, type):
    if request.method not in ['GET']:
        return JsonResponse({"error":"Method not allowed"}, status=405)

    return JsonResponse(list(Resource.objects.filter(type=type).values()), safe=False)