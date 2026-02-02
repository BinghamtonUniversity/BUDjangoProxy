from django.forms import model_to_dict
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, JsonResponse, HttpRequest, HttpResponseNotFound
from django.views.decorators.csrf import csrf_exempt
from ..models import *
from ..lib.policies_wrapper import policy
from ..policies.api_users import *
from BUDjangoProxyApp.lib.helpers import instance_to_dict
from dotenv import dotenv_values
env_values = dotenv_values(".env")


@csrf_exempt
@policy(can_get_create_api_user)
def get_create_api_users(request):
    if request.method not in ['GET','POST']:
        return JsonResponse({"error":"Method not allowed"}, status=405)

    if request.method == 'GET':
        return JsonResponse(list(APIUser.objects.filter(environment__server_name=env_values['SERVER_NAME']).all().values()), safe=False)
    elif request.method == 'POST':
        request_data = request.data
        try:
            environment = Environment.objects.get(id=int(request_data['environment_id']) if 'environment_id' in request_data else None, server_name=env_values['SERVER_NAME'])
            request_data['environment'] = environment
            del request_data['environment_id']
        except Environment.DoesNotExist:
            return JsonResponse({'error': 'Environment not found'}, status=404)

        # try:
        api_user = APIUser(**request_data)
        api_user.set_password(api_user.app_secret)

        return JsonResponse(model_to_dict(api_user), safe=False)
        # except Exception as e:
        #     return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@policy(can_manage_api_user,object_arg_name='id')
def manage_api_users(request, id):
    if request.method not in ['GET','PUT','DELETE']:
        return JsonResponse({"error":"Method not allowed"}, status=405)
    if request.method == 'GET':
        request_data = get_object_or_404(APIUser, id=id)
        request_data.encrypted_app_secret = request_data.decrypt_password()
        return JsonResponse(model_to_dict(request_data), safe=False)
    elif request.method == 'PUT':
        # try:
        api_user = APIUser.objects.filter(id=id).first()
        if api_user:
            api_user.environment_id = request.data['environment_id']
            api_user.is_active = request.data['is_active']
            api_user.app_name = request.data['app_name']
            api_user.set_password(request.data['app_secret'])
            api_user.save()
            return_dict = model_to_dict(api_user)
            return_dict['environment_id'] = int(api_user.environment_id)
            del return_dict['environment']

        return JsonResponse(return_dict,status=200)
        # except Exception as e:
        #     return JsonResponse({"error": str(e)}, status=500)

    elif request.method == 'DELETE':
        try:
            APIUser.objects.filter(id=id, environment__server_name=env_values['SERVER_NAME']).delete()
            return JsonResponse({'message': "Success"}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@policy(can_manage_api_user,object_arg_name='id')
def decrypted_app_secret(request,id):
    if request.method not in ['GET']:
        return JsonResponse({"error":"Method not allowed"}, status=405)
    try:
        api_user = APIUser.objects.filter(id=id, environment__server_name=env_values['SERVER_NAME']).first()
        return JsonResponse({'app_secret':api_user.decrypt_password()},safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
