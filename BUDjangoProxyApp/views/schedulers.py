from django.forms import model_to_dict
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, JsonResponse, HttpRequest, HttpResponseNotFound
from django.views.decorators.csrf import csrf_exempt
from BUDjangoProxyApp.lib.helpers import instance_to_dict
from ..models import *
from ..lib.policies_wrapper import policy
from ..policies.schedulers import *
from dotenv import dotenv_values
from django.utils import timezone
from BUDjangoProxyApp.lib.execute_task import execute_task
from BUDjangoProxyApp.services.DynamicLoader import DynamicAppManager

env_values = dotenv_values(".env")

@csrf_exempt
@policy(can_get_create_scheduler)
def get_create_scheduler(request):
    if request.method not in ['GET', 'POST']:
        return JsonResponse({"error":"Method not allowed"}, status=405)

    if request.method == 'GET':
        schedulers = Scheduler.objects.filter(
            api_instance__environment__server_name=env_values['SERVER_NAME'],
            api_instance__api__api_type='python'
        )
        return JsonResponse([scheduler.to_dict() for scheduler in schedulers], safe=False)
    elif request.method == 'POST':
        try:
            scheduler = Scheduler(**request.data)
            scheduler.save()

            return JsonResponse(scheduler.to_dict(), safe=False)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@policy(can_manage_scheduler,object_arg_name='id')
def get_manage_scheduler(request, id):
    if request.method not in ['GET', 'PUT','DELETE']:
        return JsonResponse({"error":"Method not allowed"}, status=405)

    if request.method == 'GET':
        return JsonResponse(Scheduler.objects.get(id=id,
                                                  api_instance__environment__server_name=env_values['SERVER_NAME'],
                                                  api_instance__api__api_type='python').to_dict(),safe=False)
    elif request.method == 'PUT':
        try:
            request_data = request.data
            Scheduler.objects.filter(id=id,
                                     api_instance__environment__server_name=env_values['SERVER_NAME'],
                                     api_instance__api__api_type='python').update(**request_data)

            return JsonResponse(Scheduler.objects.get(id=id).to_dict(), safe=False)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    elif request.method == 'DELETE':
        try:
            Scheduler.objects.filter(id=id,
                                     api_instance__environment__server_name=env_values['SERVER_NAME'],
                                     api_instance__api__api_type='python').delete()

            return JsonResponse({'message': "Success"}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
# @policy(can_manage_scheduler,object_arg_name='id')
def run_schedule(request, id):
    if request.method not in ['GET']:
        return JsonResponse({"error":"Method not allowed"}, status=405)

    if request.method == 'GET':
        try:
            schedule = Scheduler.objects.get(id=id)
            # print(schedule)
            execute_task(schedule, DynamicAppManager)
            return JsonResponse(Scheduler.objects.get(id=id).to_dict()['last_response'], safe=False)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)