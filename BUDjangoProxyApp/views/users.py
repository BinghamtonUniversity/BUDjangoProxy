from django.forms import model_to_dict
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, JsonResponse, HttpRequest, HttpResponseNotFound
from django.views.decorators.csrf import csrf_exempt
from ..models import *
from ..lib.policies_wrapper import policy
from ..policies.users import *

@csrf_exempt
@policy(can_get_create_users)
def get_create_users(request):
    if request.method not in ['GET', 'POST']:
        return JsonResponse({"error":"Method not allowed"}, status=405)

    if request.method == 'GET':
        return JsonResponse(list(User.objects.all().values()), safe=False)
    elif request.method == 'POST':
        user = User(**request.data)
        user.save()
        return JsonResponse(model_to_dict(user), safe=False)

@csrf_exempt
@policy(can_manage_user, object_arg_name='id')
def get_manage_user(request, id):
    if request.method not in ['GET','PUT','DELETE']:
        return JsonResponse({"error":"Method not allowed"}, status=405)

    if request.method == 'GET':
        request_data = get_object_or_404(User, id=id)
        return JsonResponse(model_to_dict(request_data),safe=False)
    elif request.method == 'PUT':
        request_data = request.data
        User.objects.filter(id=id).update(**request_data)
        return JsonResponse(model_to_dict(User.objects.get(id=id)), safe=False)
    elif request.method == 'DELETE':
        User.objects.filter(id=id).delete()
        return JsonResponse({'message': "Success"}, status=200)
