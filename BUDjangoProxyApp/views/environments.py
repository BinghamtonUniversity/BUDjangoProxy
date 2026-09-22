from django.utils import timezone
from django.forms import model_to_dict
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, JsonResponse, HttpRequest, HttpResponseNotFound
from django.views.decorators.csrf import csrf_exempt
from ..models import *
from ..lib.policies_wrapper import policy
from ..policies.environments import *

from dotenv import dotenv_values
env_values = dotenv_values(".env")

@csrf_exempt
@policy(can_get_create_environment)
def get_create_environments(request):
    if request.method not in ['GET','POST']:
        return JsonResponse({"error":"Method not allowed"}, status=405)

    if request.method == 'GET':
        return JsonResponse(list(Environment.objects.filter(server_name=env_values['SERVER_NAME']).all().values()), safe=False)
    elif request.method == 'POST':
        try:
            environment = Environment(**request.data)
            environment.updated_at = timezone.now()
            environment.created_at = timezone.now()
            environment.server_name = env_values['SERVER_NAME']
            environment.save()
            return JsonResponse(model_to_dict(environment), safe=False)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@policy(can_manage_environment, object_arg_name='id')
def get_manage_environment(request,id):
    if request.method not in ['GET','PUT','DELETE']:
        return JsonResponse({"error":"Method not allowed"}, status=405)

    if request.method == 'GET':
        environment = get_object_or_404(Environment, id=id, server_name=env_values['SERVER_NAME'])
        return JsonResponse(model_to_dict(environment), safe=False)
    elif request.method == 'PUT':
        try:
            environment = Environment.objects.filter(id=id).first()
            if environment:
                environment.domain = request.data['domain']
                environment.name = request.data['name']
                environment.type = request.data['type']
                environment.updated_at = timezone.now()
                environment.save()
            return JsonResponse(model_to_dict(environment), safe=False)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    elif request.method == 'DELETE':
        try:
            Environment.objects.filter(id=id, server_name=env_values['SERVER_NAME']).delete()
            return JsonResponse({'message': "Success"}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
