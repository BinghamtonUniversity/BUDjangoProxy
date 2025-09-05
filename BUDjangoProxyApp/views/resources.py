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
        api_instance = Resource(**request.data)
        api_instance.config['pass'] = LaravelEncryptor().encrypt(api_instance.config['pass'])
        api_instance.save()
        return JsonResponse(model_to_dict(api_instance), safe=False)

@csrf_exempt
@policy(can_manage_resource,object_arg_name='id')
def get_manage_resource(request, id):
    if request.method not in ['GET','PUT','DELETE']:
        return JsonResponse({"error":"Method not allowed"}, status=405)

    if request.method == 'GET':
        request_data = get_object_or_404(Resource, id=id)
        return JsonResponse(model_to_dict(request_data),safe=False)
    elif request.method == 'PUT':
        request_data = request.data
        request_data['config']['pass'] = LaravelEncryptor().encrypt(request_data['config']['pass'])
        Resource.objects.filter(id=id).update(**request_data)
        return JsonResponse(model_to_dict(Resource.objects.get(id=id)), safe=False)
    elif request.method == 'DELETE':
        Resource.objects.filter(id=id).delete()
        return JsonResponse({'message': "Success"}, safe=False)

@csrf_exempt
@policy(can_get_create_resource)
def get_resources_by_type(request, type):
    if request.method not in ['GET']:
        return JsonResponse({"error":"Method not allowed"}, status=405)

    return JsonResponse(list(Resource.objects.filter(type=type).values()), safe=False)