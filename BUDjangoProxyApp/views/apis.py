import json
from urllib import request
from django.forms import model_to_dict
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse, HttpRequest, HttpResponseNotFound
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from django.core.exceptions import FieldError
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from ..models import *

@csrf_exempt
@api_view(['GET','POST'])
def get_create_apis(request):
    if request.method == 'GET':
        return JsonResponse(list(API.objects.all().values()), safe=False)
    elif request.method == 'POST':
        request_data = request.data

        request_data['created_by_id'] = 1
        request_data['updated_by_id'] = 1
        request_data['user_id'] = 1
        api = API(**request.data)
        api.save()
        api_version  = APIVersion(api= api,
                                  version_files=[],
                                  resources=[],
                                  options = [],
                                  version_models = [],
                                  version_views = [],
                                  version_urls=[],
                                  created_by_id=1,
                                  updated_by_id=1,
                                  stable=False)
        api_version.save()
        return JsonResponse(model_to_dict(api), safe=False)

@csrf_exempt
@api_view(['GET', 'PUT','DELETE'])
def get_manage_api(request, id):
    if request.method == 'GET':
        request_data = get_object_or_404(API, id=id)
        return JsonResponse(model_to_dict(request_data),safe=False)
    elif request.method == 'PUT':
        request_data = request.data
        request_data['updated_at'] = timezone.now()
        API.objects.filter(id=id, api_type='python').update(**request_data)
        return JsonResponse(model_to_dict(API.objects.get(id=request_data['id'])), safe=False)
    elif request.method == 'DELETE':
        API.objects.filter(id=id, api_type='python').delete()
        return JsonResponse({'message': "Success"}, code=200)


@csrf_exempt
@api_view(['GET'])
def get_api_versions(request):
    return JsonResponse(list(APIVersion.objects.all().values()), safe=False)


@csrf_exempt
@api_view(['GET'])
def get_latest_api_version(request,id):
    try:
        return JsonResponse(model_to_dict(APIVersion.objects.filter(api_id=id).latest('updated_at')),safe=False)
    except APIVersion.DoesNotExist:
        return HttpResponseNotFound()

@csrf_exempt
@api_view(['PUT'])
def publish_api_version(request,id):
    request_data = request.data
    try:
        api_version =  APIVersion.objects.filter(api=id, stable=False).latest('updated_at')
        api_version.summary = request_data['summary']
        api_version.description = request_data['description']
        api_version.stable = True
        api_version.save()
        return JsonResponse(model_to_dict(api_version), safe=False)

    except APIVersion.DoesNotExist:
        return HttpResponseNotFound()

@csrf_exempt
@api_view([ 'PUT'])
def manage_api_version_code(request, id):
    try:
        api_version = APIVersion.objects.filter(api=id, stable=False).latest('updated_at')
    except APIVersion.DoesNotExist:
        api_version = APIVersion(api_id=id, stable=False, created_by_id=1, updated_by_id=1)
        api_version.stable = False

    api_version.version_models = request.data['version_models'] if 'version_models' in request.data else []
    api_version.version_urls = request.data['version_urls'] if 'version_urls' in request.data else []
    api_version.version_views = request.data['version_views'] if 'version_views' in request.data else []
    api_version.version_files = request.data['version_files'] if 'version_files' in request.data else []
    api_version.resources = request.data['resources'] if 'resources' in request.data else []
    api_version.options = request.data['options'] if 'options' in request.data else []
    api_version.updated_at = timezone.now()

    api_version.save()

    return JsonResponse(model_to_dict(api_version), safe=False)