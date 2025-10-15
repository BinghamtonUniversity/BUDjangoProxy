from django.contrib import admin
from django.urls import path
from django.urls import re_path
from django.http import JsonResponse
from .views import *

def index(request):
    return JsonResponse({'message': 'Welcome to Dynamic App Manager'})

urlpatterns = [
    # API USERS OPERATIONS

    # PUT, DELETE api_user -> Update or delete API User
    path('api_users/<int:id>', view=api_users.manage_api_users, name='manage_api_users'),
    # GET, POST api_user -> Get or create API User
    path('api_users', view=api_users.get_create_api_users, name='get_create_api_users'),
    # GET api_user->decrypted_secret
    path('api_users/<int:id>/decrypted_secret', view=api_users.decrypted_app_secret, name='decrypted_app_secret'),

    # ENVIRONMENTS OPERATIONS
    # GET, POST environment -> Get or create API User
    path('environments/<int:id>', view=environments.get_manage_environment, name='manage_environments'),
    # PUT, DELETE environment -> Update or delete API User
    path('environments', view=environments.get_create_environments, name='get_create_environments'),

    # APIs OPERATIONS
    # GET, POST APIs view
    path('apis', view=apis.get_create_apis, name='get_create_apis'),
    # Put, Delete API View
    path('apis/<int:id>', view=apis.get_manage_api, name='manage_apis'),

    # API VERSIONS OPERATIONS
    # PUT API Version Code for the non-stable APIs
    path('apis/<int:id>/code', view=apis.manage_api_version_code, name='manage_api_version'),
    # GET API Version -> Get all the version of the API
    path('apis/<int:id>/versions', view=apis.get_api_versions, name='get_api_versions'),
    # GET ALL API VERSIONS
    path('api_versions', view=apis.get_all_api_versions, name='get_all_api_versions'),

    path('apis/<int:api_id>/versions/<int:version_id>', view=apis.get_api_version_code, name='get_api_version_code'),
    # GET API Version -> get the latest API version
    path('apis/<int:id>/versions/latest', view=apis.get_latest_api_version, name='get_latest_api_version'),
    # PUT API Version -> Publish the API
    path('apis/<int:id>/publish', view=apis.publish_api_version, name='publish_api_version'),

    # GET/CREATE API Developer
    path('apis/<int:api_id>/developers', view=apis.get_create_api_developer, name='get_create_api_developer'),
    # DELETE API Developer
    path('apis/<int:api_id>/developers/<int:user_id>', view=apis.delete_api_developer, name='delete_api_developers'),


    # API INSTANCES Operations
    # GET, POST API Instance(s)
    path('api_instances', view=api_instances.get_create_api_instances, name='get_create_api_instances'),
    # GET, PUT, DELETE API Instance by ID
    path('api_instances/<int:id>', view=api_instances.get_manage_api_instance, name='get_manage_api_instance'),

    # RESOURCES Operations
    # GET, POST Resources
    path('resources', view=resources.get_create_resources, name='get_create_resources'),
    # GET, PUT, DELETE Resources ID
    path('resources/<int:id>', view=resources.get_manage_resource, name='get_manage_resources'),
    # GET Resources by Type
    path('resources/type/<str:type>', view=resources.get_resources_by_type, name='get_resources_by_type'),

    #USERS Operations
    # GET, POST Users
    path('users', view=users.get_create_users, name='get_create_users'),
    # GET, PUT, DELETE Users ID
    path('users/<int:id>', view=users.get_manage_user, name='get_manage_user'),
    path('users/<int:user_id>/apis', view=users.get_user_apis, name='get_user_apis'),

    #Schedulers Operations
    # GET, POST Schedulers
    path('schedulers', view=schedulers.get_create_scheduler, name='get_create_scheduler'),

    # GET, PUT, DELETE Schedulers by ID
    path('schedulers/<int:id>', view=schedulers.get_manage_scheduler, name='get_manage_scheduler'),

    #Activity Logs Operations
    # GET Activity Logs
    path('activity_logs', view=activity_logs.get_create_activity_log, name='get_create_activity_log')
]