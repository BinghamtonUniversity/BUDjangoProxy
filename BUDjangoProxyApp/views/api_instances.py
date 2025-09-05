from django.forms import model_to_dict
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, JsonResponse, HttpRequest, HttpResponseNotFound
from django.views.decorators.csrf import csrf_exempt
from ..models import *
from ..lib.policies_wrapper import policy
from ..policies.api_instances import *

@csrf_exempt
@policy(can_get_create_api_instance)
def get_create_api_instances(request):
    if request.method not in ['GET', 'POST']:
        return JsonResponse({"error":"Method not allowed"}, status=405)

    if request.method == 'GET':
        return JsonResponse(list(APIInstance.objects.all().values()), safe=False)
    elif request.method == 'POST':
        api_instance = APIInstance(**request.data)
        api_instance.save()
        return JsonResponse(model_to_dict(api_instance), safe=False)

@csrf_exempt
@policy(can_manage_api_instance,object_arg_name='id')
def get_manage_api_instance(request, id):
    if request.method not in ['GET', 'PUT','DELETE']:
        return JsonResponse({"error":"Method not allowed"}, status=405)

    if request.method == 'GET':
        request_data = get_object_or_404(APIInstance, id=id)
        return JsonResponse(model_to_dict(request_data),safe=False)
    elif request.method == 'PUT':
        request_data = request.data
        APIInstance.objects.filter(id=id).update(**request_data)
        return JsonResponse(model_to_dict(APIInstance.objects.get(id=id)), safe=False)
    elif request.method == 'DELETE':
        APIInstance.objects.filter(id=id).delete()
        return JsonResponse({'message': "Success"}, status=200)