from django.utils import timezone
from django.forms import model_to_dict
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, JsonResponse, HttpRequest, HttpResponseNotFound
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from ..models import *

@csrf_exempt
@api_view(['GET', 'POST'])
def get_create_environments(request):
    if request.method == 'GET':
        return JsonResponse(list(Environment.objects.all().values()), safe=False)
    elif request.method == 'POST':
        environment = Environment(**request.data)
        environment.save()
        return JsonResponse(model_to_dict(environment), safe=False)

@csrf_exempt
@api_view(['GET','PUT','DELETE'])
def get_manage_environment(request):
    if request.method == 'GET':
        request_data = get_object_or_404(Environment, id=id)
        return JsonResponse(model_to_dict(request_data), safe=False)
    elif request.method == 'PUT':
        environment = Environment.objects.filter(id=id).first()
        if environment:
            # print(request.data)
            environment.domain = request.data['domain']
            environment.name = request.data['name']
            environment.type = request.data['type']
            environment.updated_at = timezone.now()
            environment.save()
        return JsonResponse({
            model_to_dict(environment)
        }, status=200)
    elif request.method == 'DELETE':
        request_data = request.data
        Environment.objects.filter(id=request_data['id']).delete()
        return JsonResponse({'message': "Success"}, code=200)
