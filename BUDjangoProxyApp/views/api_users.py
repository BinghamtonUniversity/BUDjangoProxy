from django.forms import model_to_dict
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, JsonResponse, HttpRequest, HttpResponseNotFound
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from ..models import *

@csrf_exempt
@api_view(['GET', 'POST'])
def get_create_api_users(request):
    if request.method == 'GET':
        return JsonResponse(list(APIUser.objects.all().values()), safe=False)
    elif request.method == 'POST':
        request_data = request.data
        try:
            environment = Environment.objects.get(id=int(request_data['environment_id']) if 'environment_id' in request_data else None)
            request_data['environment'] = environment
            del request_data['environment_id']
        except Environment.DoesNotExist:
            return JsonResponse({'error': 'Environment not found'}, status=404)

        api_user = APIUser(**request_data)
        api_user.set_password(api_user.app_secret)

        return JsonResponse(model_to_dict(api_user), safe=False)

@csrf_exempt
@api_view(['GET', 'PUT','DELETE'])
def manage_api_users(request, id):
    if request.method == 'GET':
        request_data = get_object_or_404(APIUser, id=id)
        request_data.encrypted_app_secret = request_data.decrypt_password()
        return JsonResponse(model_to_dict(request_data), safe=False)
    elif request.method == 'PUT':
        api_user = APIUser.objects.filter(id=id).first()
        if api_user:
            print(request.data)
            api_user.app_name = request.data['app_name']
            api_user.set_password(request.data['app_secret'])
            api_user.save()
        return JsonResponse({
            'message': "Success"
        },status=200)
    elif request.method == 'DELETE':
        request_data = request.data
        APIUser.objects.filter(id=request_data['id']).delete()
        return JsonResponse({'message': "Success"}, code=200)

@csrf_exempt
@api_view(['GET'])
def decrypted_app_secret(request,id):
    try:
        api_user = APIUser.objects.filter(id=id).first()
        print(api_user.decrypt_password())
        return JsonResponse({'app_secret':api_user.decrypt_password()},safe=False)
    except APIUser.DoesNotExist:
        return HttpResponseNotFound()
