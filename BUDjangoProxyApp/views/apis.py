import datetime
from django.utils.dateparse import parse_datetime
import json
from urllib import request
from django.forms import model_to_dict
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse, HttpRequest, HttpResponseNotFound
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import FieldError
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from datetime import timezone as dt_timezone
from ..models import *
from ..lib.policies_wrapper import policy
from ..policies.apis import *

@csrf_exempt
@policy(can_get_create_apis)
def get_create_apis(request):
    if request.method not in ['GET', 'POST']:
        return JsonResponse({"error":"Method not allowed"}, status=405)

    if request.method == 'GET':
        return JsonResponse(list(API.objects.filter(api_type='python',deleted_at=None).all().values()), safe=False)

    elif request.method == 'POST':
        # try:
        request_data = request.data
        request_data['created_by'] = request.user
        request_data['updated_by'] = request.user
        api = API(**request_data)
        api.api_type = 'python'
        api.created_at = datetime.now()
        api.updated_at = datetime.now()
        api.save()

        api_version  = APIVersion(api= api,
                                  version_files=[],
                                  resources=[],
                                  options = None,
                                  version_models = [],
                                  version_views = [],
                                  version_urls=[],
                                  user_id = request_data['user_id'],
                                  # created_by=request.user,
                                  updated_by=request.user,
                                  created_at=datetime.now(),
                                  updated_at=datetime.now(),
                                  stable=False)
        api_version.save()
        api_developer = APIDeveloper(api=api, user=request.user)
        api_developer.save()

        return JsonResponse(api.to_dict(), safe=False)
        # except Exception as e:
        #     return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@policy(can_manage_api, object_arg_name='id')
def get_manage_api(request, id):
    if request.method not in ['GET', 'PUT','DELETE']:
        return JsonResponse({"error":"Method not allowed"}, status=405)

    if request.method == 'GET':
        api = get_object_or_404(API, id=id, deleted_at=None)
        return JsonResponse(api.to_dict(),safe=False)
    elif request.method == 'PUT':
        try:
            request_data = request.data
            request_data['updated_at'] = timezone.now()
            API.objects.filter(id=id, api_type='python',deleted_at=None).update(**request_data)
            return JsonResponse(API.objects.get(id=id).to_dict(), safe=False)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    elif request.method == 'DELETE':
        try:
            if APIInstance.objects.filter(api_id=id).exists():
                return JsonResponse("This API is in use by an API Instance, please delete the instance first!", status=400, safe=False)

            API.objects.filter(id=id, api_type='python', deleted_at=None).update(deleted_at=datetime.now())
            return JsonResponse({'message': "Success"}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def get_api_versions(request, id):
    if request.method not in ['GET']:
        return JsonResponse({"error":"Method not allowed"}, status=405)

    return JsonResponse(list(APIVersion.objects.filter(api_id=id, api__api_type='python',stable=True).values('id','description','summary','stable','created_at')), safe=False)

@csrf_exempt
def get_api_version_code(request, version_id):
    if request.method not in ['GET']:
        return JsonResponse({"error":"Method not allowed"}, status=405)
    api_version = get_object_or_404(APIVersion, id=version_id, api__api_type='python')
    return JsonResponse(model_to_dict(api_version), safe=False)


@csrf_exempt
@policy(can_get_create_apis)
def get_latest_api_version(request,id):
    if request.method not in ['GET']:
        return JsonResponse({"error":"Method not allowed"}, status=405)
    try:
        return JsonResponse(model_to_dict(APIVersion.objects.filter(api_id=id).latest('created_at')),safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@policy(can_manage_api, object_arg_name='id')
def publish_api_version(request,id):
    if request.method not in ['PUT']:
        return JsonResponse({"error":"Method not allowed"}, status=405)

    request_data = request.data
    try:
        api_version =  APIVersion.objects.filter(api=id, stable=False).latest('updated_at')
        api_version.summary = request_data['summary']
        api_version.description = request_data['description']
        api_version.stable = True
        api_version.save()
        return JsonResponse(model_to_dict(api_version), safe=False)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@policy(can_manage_api, object_arg_name='id')
def manage_api_version_code(request, id):
    if request.method not in ['PUT']:
        return JsonResponse({"error":"Method not allowed"}, status=405)

    api_version = APIVersion.objects.filter(api=id).latest('created_at')


    if 'updated_at' not in request.data and 'force' not in request.data:
        return JsonResponse({"error":model_to_dict(api_version)}, status=403)

    local = api_version.updated_at
    if request.data.get('updated_at') is None:
        request.data['updated_at'] = datetime.datetime.now(dt_timezone.utc).isoformat()

    incoming = parse_datetime(request.data.get('updated_at'))

    print(f"Incoming: {incoming}", f"Local: {local}")
    if api_version is None or api_version.stable:
        api_version = APIVersion(api_id=id, stable=False,
                                 created_by=request.user,
                                 updated_by=request.user,
                                 created_at=timezone.now(),
                                 updated_at=timezone.now())

    elif not (incoming >= local or 'force' in request.data):
        return JsonResponse({"error": model_to_dict(api_version)}, status=409)
    try:
        api_version.version_models = request.data.get('version_models')
        api_version.version_urls = request.data.get('version_urls')
        api_version.version_views = request.data.get('version_views')
        api_version.version_files = request.data.get('version_files')
        api_version.resources = request.data.get('resources')
        api_version.options = request.data.get('options')
        api_version.updated_at = timezone.now()
        api_version.updated_by = request.user
        api_version.save()

        return JsonResponse(model_to_dict(APIVersion.objects.get(id=api_version.id)), safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@policy(can_api_developers, object_arg_name='api_id')
def get_api_developers(request, api_id):
    if request.method not in ['GET','POST']:
        return JsonResponse({"error":"Method not allowed"}, status=405)

    if request.method == 'GET':
        return JsonResponse(list(APIDeveloper.objects.filter(api_id=api_id).values()), safe=False)

@csrf_exempt
@policy(can_manage_api_developers, object_arg_name='api_id')
def create_delete_api_developer(request, api_id, user_id):
    if request.method not in ['GET','POST','DELETE']:
        return JsonResponse({"error":"Method not allowed"}, status=405)

    if request.method == 'GET':
        return JsonResponse(list(APIDeveloper.objects.filter(api_id=api_id, user_id=user_id).values()), safe=False)

    elif request.method == 'POST':
        try:
            api_developer = APIDeveloper(api_id=api_id, user_id=user_id)
            api_developer.save()
            return JsonResponse(model_to_dict(api_developer), safe=False)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    elif request.method == 'DELETE':
        try:
            APIDeveloper.objects.filter(api_id=api_id, user_id=user_id).delete()
            return JsonResponse({'message': "Success"}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def get_all_api_versions(request):
    if request.method not in ['GET']:
        return JsonResponse({"error":"Method not allowed"}, status=405)

    return JsonResponse(list(APIVersion.objects.all().values('id','description','summary','stable','created_at')), safe=False)