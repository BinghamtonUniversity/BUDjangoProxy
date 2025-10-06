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
def get_create_activity_log(request):
    if request.method not in ['GET', 'POST']:
        return JsonResponse({"error":"Method not allowed"}, status=405)

    if request.method == 'GET':
        return JsonResponse(list(ActivityLog.objects.all().values()), safe=False)