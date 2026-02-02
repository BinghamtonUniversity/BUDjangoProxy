from django.forms import model_to_dict
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, JsonResponse, HttpRequest, HttpResponseNotFound
from django.views.decorators.csrf import csrf_exempt
from BUDjangoProxyApp.lib.helpers import instance_to_dict
from ..models import *
from ..lib.policies_wrapper import policy
from ..policies.schedulers import *
from dotenv import dotenv_values
env_values = dotenv_values(".env")

@csrf_exempt
@policy(can_get_create_scheduler)
def get_create_scheduler(request):
    if request.method not in ['GET', 'POST']:
        return JsonResponse({"error":"Method not allowed"}, status=405)

    if request.method == 'GET':
        return JsonResponse(list(Scheduler.objects.filter(api_instance__environment__server_name=env_values['SERVER_NAME']).all().values()), safe=False)
    elif request.method == 'POST':
        try:
            scheduler = Scheduler(**request.data)
            scheduler.save()

            return JsonResponse(model_to_dict(scheduler), safe=False)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@policy(can_manage_scheduler,object_arg_name='id')
def get_manage_scheduler(request, id):
    if request.method not in ['GET', 'PUT','DELETE']:
        return JsonResponse({"error":"Method not allowed"}, status=405)

    if request.method == 'GET':
        return JsonResponse(model_to_dict(Scheduler.objects.get(id=id,api_instance__environment__server_name=env_values['SERVER_NAME'])),safe=False)
    elif request.method == 'PUT':
        try:
            request_data = request.data
            APIInstance.objects.filter(id=id, environment__server_name=env_values['SERVER_NAME']).update(**request_data)

            return JsonResponse(model_to_dict(Scheduler.objects.get(id=id)), safe=False)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    elif request.method == 'DELETE':
        try:
            Scheduler.objects.filter(id=id, api_instance__environment__server_name=env_values['SERVER_NAME']).delete()

            return JsonResponse({'message': "Success"}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)