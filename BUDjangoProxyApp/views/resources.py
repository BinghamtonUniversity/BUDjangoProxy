from django.forms import model_to_dict
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, JsonResponse, HttpRequest, HttpResponseNotFound
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from ..models import *

@csrf_exempt
@api_view(['GET', 'POST'])
def get_create_resources(request):
    if request.method == 'GET':
        return JsonResponse(list(Resource.objects.all().values()), safe=False)
    elif request.method == 'POST':
        api_instance = Resource(**request.data)
        api_instance.save()
        return JsonResponse(model_to_dict(api_instance), safe=False)

@csrf_exempt
@api_view(['GET', 'PUT','DELETE'])
def get_manage_resource(request, id):
    if request.method == 'GET':
        request_data = get_object_or_404(Resource, id=id)
        return JsonResponse(model_to_dict(request_data),safe=False)
    elif request.method == 'PUT':
        request_data = request.data
        Resource.objects.filter(id=id).update(**request_data)
        return JsonResponse(model_to_dict(Resource.objects.get(id=id)), safe=False)
    elif request.method == 'DELETE':
        Resource.objects.filter(id=id).delete()
        return JsonResponse({'message': "Success"}, code=200)

@csrf_exempt
@api_view(['GET',])
def get_resources_by_type(request, type):
    return JsonResponse(list(Resource.objects.filter(type=type).values()), safe=False)