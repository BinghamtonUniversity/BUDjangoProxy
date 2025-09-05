from django.utils import timezone
from django.forms import model_to_dict
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, JsonResponse, HttpRequest, HttpResponseNotFound
from django.views.decorators.csrf import csrf_exempt
from ..models import *
from ..lib.policies_wrapper import policy
from ..policies.environments import *

@csrf_exempt
@policy(can_get_create_environment)
def get_create_environments(request):
    if request.method not in ['GET','POST']:
        return JsonResponse({"error":"Method not allowed"}, status=405)

    if request.method == 'GET':
        return JsonResponse(list(Environment.objects.all().values()), safe=False)
    elif request.method == 'POST':
        environment = Environment(**request.data)
        environment.save()
        return JsonResponse(model_to_dict(environment), safe=False)

@csrf_exempt
@policy(can_manage_environment, object_arg_name='id')
def get_manage_environment(request,id):
    if request.method not in ['GET','PUT','DELETE']:
        return JsonResponse({"error":"Method not allowed"}, status=405)

    if request.method == 'GET':
        environment = get_object_or_404(Environment, id=id)
        return JsonResponse(model_to_dict(environment), safe=False)
    elif request.method == 'PUT':
        environment = Environment.objects.filter(id=id).first()
        if environment:
            environment.domain = request.data['domain']
            environment.name = request.data['name']
            environment.type = request.data['type']
            environment.updated_at = timezone.now()
            environment.save()
        return JsonResponse(model_to_dict(environment), safe=False)
    elif request.method == 'DELETE':
        request_data = request.data
        Environment.objects.filter(id=id).delete()
        return JsonResponse({'message': "Success"}, status=200)
