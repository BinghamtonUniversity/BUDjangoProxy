from django.forms import model_to_dict
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, JsonResponse, HttpRequest, HttpResponseNotFound
from django.views.decorators.csrf import csrf_exempt
from BUDjangoProxyApp.lib.helpers import instance_to_dict
from ..models import *
# from ..lib.policies_wrapper import policy
# from ..policies.schedulers import *

# @csrf_exempt
# @policy(can_get_create_api_instance)
def get_create_scheduler(request):
    if request.method not in ['GET', 'POST']:
        return JsonResponse({"error":"Method not allowed"}, status=405)

    if request.method == 'GET':
        return JsonResponse(list(Scheduler.objects.all().values()), safe=False)
    elif request.method == 'POST':
        try:
            scheduler = Scheduler(**request.data)
            scheduler.save()

            return JsonResponse(model_to_dict(scheduler), safe=False)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

# @csrf_exempt
# @policy(can_manage_api_instance,object_arg_name='id')
def get_manage_scheduler(request, id):
    if request.method not in ['GET', 'PUT','DELETE']:
        return JsonResponse({"error":"Method not allowed"}, status=405)

    if request.method == 'GET':
        return JsonResponse(model_to_dict(Scheduler.objects.get(id=id)),safe=False)
    elif request.method == 'PUT':
        try:
            request_data = request.data
            APIInstance.objects.filter(id=id).update(**request_data)

            return JsonResponse(model_to_dict(Scheduler.objects.get(id=id)), safe=False)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    elif request.method == 'DELETE':
        try:
            Scheduler.objects.filter(id=id).delete()

            return JsonResponse({'message': "Success"}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)