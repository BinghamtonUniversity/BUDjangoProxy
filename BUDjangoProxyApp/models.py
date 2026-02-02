import json
from os import environ

from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.forms.models import model_to_dict
from BUDjangoProxyApp.middleware.request_context import get_request_user_info, get_request_context
from BUDjangoProxyApp.services.LaravelEncryptor import LaravelEncryptor
from BUDjangoProxy.settings import env_values
from .lib import helpers
import logging
import bcrypt

logger = logging.getLogger(__name__)


class User(models.Model):
    id = models.AutoField(primary_key=True)
    unique_id = models.CharField(max_length=11, unique=True, db_column='unique_id')
    name = models.CharField(max_length=200)
    username = models.CharField(max_length=11, unique=True ,null=False, blank=False)
    email = models.EmailField(max_length=200, null=True, blank=True)
    admin = models.BooleanField(default=False, db_column='admin')
    active = models.BooleanField(default=True, db_column='active')
    developer = models.BooleanField(default=False, db_column='developer')

    class Meta:
        db_table = 'users'

    def __str__(self):
        return f"{self.name} - {self.unique_id}"


class Environment(models.Model):
    environment_type = (
        ('dev', 'Development'),
        ('test', 'Testing'),
        ('prod', 'Production'),
    )
    id = models.AutoField(primary_key=True)
    domain = models.CharField(max_length=200, db_index=True, unique=True)
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=10, choices=environment_type, default='dev')
    server_name = models.CharField(max_length=200, null=False, blank=False, default=env_values['SERVER_NAME'])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} - {self.type}"

    class Meta:
        db_table = 'environments'


class API(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=False)
    description = models.CharField(max_length=255, blank=True, null=True)
    tags = models.CharField(max_length=255, blank=True, null=True)
    api_type = models.CharField(max_length=20, default='php', blank=False, null=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE,db_column='user_id', db_constraint=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name='api_created_by',to_field='id', db_column='created_by',db_constraint=True)
    updated_by = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name='api_updated_by', to_field='id', db_column='updated_by',db_constraint=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.name} - {self.id}'

    class Meta:
        db_table = "apis"
        ordering = ['name']

class APIVersion(models.Model):
    id = models.AutoField(primary_key=True)
    api = models.ForeignKey(API, on_delete=models.CASCADE, related_name='api_versions',parent_link=True, db_index=True,db_constraint=True)
    summary = models.CharField(max_length=255, null=True, blank=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    stable = models.BooleanField(default=False, db_index=True)
    version_models = models.JSONField()
    version_views = models.JSONField(db_column='functions', default=list, null=True, blank=True)
    version_urls = models.JSONField(db_column='routes', default=list, null=True, blank=True)
    options = models.JSONField(db_column='options' ,null=True, blank=True)
    version_files = models.JSONField(db_column='files', null=True, blank=True)
    resources = models.JSONField(default=dict, null=True, blank=True)
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_version_created_by', db_column='user_id',db_constraint=True)
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_version_updated_by', db_column='updated_by',db_constraint=True)

    def __str__(self):
        return f"{self.id} - {self.api.name}"

    class Meta:
        db_table = "api_versions"

class APIInstance(models.Model):
    error_types =environment_type = (
        ('none', 'None'),
        ('all', 'All')
    )

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, null=True)
    route = models.CharField(max_length=255, db_column='slug')
    api = models.ForeignKey(API, on_delete=models.CASCADE, related_name='api_instance',db_constraint=True)
    api_version_id = models.ForeignKey(APIVersion, to_field='id', verbose_name='api_version', default=None, null=True, db_column='api_version_id', blank=True, on_delete=models.CASCADE, related_name='version_instance',db_constraint=True)
    environment = models.ForeignKey(Environment, on_delete=models.CASCADE, db_index=True, related_name='environment_instance',db_constraint=True)
    resources = models.JSONField(encoder=json.JSONEncoder, decoder=json.JSONDecoder, null=True, blank=False, default=None)
    options = models.JSONField(encoder=json.JSONEncoder, decoder=json.JSONDecoder, null=True, blank=False, default=None)
    route_user_map = models.JSONField(default=list, encoder=json.JSONEncoder, decoder=json.JSONDecoder, db_column='route_user_map', null=True)
    public =models.BooleanField(default=False)
    errors = models.CharField(max_length=10, choices=error_types, default='none')
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "api_instances"
        unique_together = (('route', 'environment'),)

    def __str__(self):
        return f"{self.name} ({self.environment.type})"

    @property
    def api_version(self):
        if self.api_version_id:
            return self.api_version_id

        return self.get_instance_version()


    def get_instance_version(self):
        if self.api_version_id is None:
            try:

                return APIVersion.objects.filter(api=self.api).latest('created_at')
            except APIVersion.DoesNotExist:
                return None
        elif self.api_version_id == 0:
            try:
                return APIVersion.objects.filter(api=self.api, stable=True).latest('updated_at')
            except APIVersion.DoesNotExist:
                return None
        else:
            return self.api_version_id

    def get_instance_version_api(self):
        return self.api_version_id.api


class APIDeveloper(models.Model):
    id = models.AutoField(primary_key=True)
    api_developer = models.ForeignKey(User, db_column='user_id', to_field='id', on_delete=models.CASCADE,db_constraint=True)
    api = models.ForeignKey(API, db_column='api_id', to_field='id', on_delete=models.CASCADE,db_constraint=True)

    class Meta:
        unique_together = (('api_developer', 'api'))
        db_table = 'api_developers'

ENVIRONMENT_TYPE = (
        ('dev', 'Development'),
        ('test', 'Testing'),
        ('prod', 'Production'),
    )

class Resource(models.Model):
    RESOURCE_TYPE_CHOICES = [
        ('oracle', 'Oracle'),
        ('mysql', 'MySQL'),
        ('sqlsrv', 'SQL Server'),
        ('secret', 'Secret'),
        ('value', 'Value'),
        ('rest', 'REST')
    ]
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    resource_type = models.CharField(
        max_length=10,
        choices=RESOURCE_TYPE_CHOICES,
        default='mysql',
        db_index=True
    )
    type = models.CharField(
        max_length=10,
        choices=ENVIRONMENT_TYPE,
        default='dev',
        db_index=True
    )
    config = models.JSONField(default=None, encoder=DjangoJSONEncoder)

    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f" {self.name}"

    class Meta:
        db_table = 'resources'

    # def


class APIUser(models.Model):
    id = models.AutoField(primary_key=True)
    app_name = models.CharField(max_length=255, unique=True, null=False,db_column='app_name',default='api_user')
    app_secret = models.CharField(max_length=255, db_column='app_secret',null=True)  # For storing hashed passwords
    encrypted_app_secret = models.CharField(max_length=255, db_column='encrypted_app_secret',null=True)
    environment = models.ForeignKey(Environment, on_delete=models.CASCADE, db_index=True, null=False,
                                    related_name='environment_users',
                                    default=1,
                                    db_constraint=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'api_users'
        ordering = ['app_name']

    def set_password(self, raw_password):
        """
        Hashes and sets the password.
        """
        encryption = LaravelEncryptor(env_values['LARAVEL_APP_KEY'])
        self.encrypted_app_secret = encryption.encrypt(raw_password)
        self.app_secret = encryption.hashMaker(raw_password)
        self.save()

    def check_password(self, raw_password):
        """Check if a password matches a stored Bcrypt hash."""
        try:
            # Convert inputs to bytes
            password_bytes = raw_password.encode('utf-8')
            hashed_bytes = self.app_secret.encode('utf-8')

            return bcrypt.checkpw(password_bytes, hashed_bytes)
        except ValueError as e:
            # Handle invalid hash format (e.g., wrong length or prefix)
            return False

    def decrypt_password(self):
        encryption = LaravelEncryptor(env_values['LARAVEL_APP_KEY'])
        return encryption.decrypt(self.encrypted_app_secret)

    def __str__(self):
        return self.app_name

class Scheduler(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    cron = models.CharField(max_length=255)
    api_instance = models.ForeignKey(APIInstance, to_field='id',db_column='api_instance_id', on_delete=models.CASCADE,db_constraint=True)
    route = models.CharField(max_length=255, null=True, blank=True)
    args = models.JSONField(default=[], encoder=DjangoJSONEncoder, null=True, blank=True)
    verb = models.CharField(default='GET', max_length=255)
    enabled = models.BooleanField(default=True, db_column='enabled')
    last_exec_cron = models.DateTimeField(null=True)
    last_exec_start = models.DateTimeField(null=True)
    last_exec_stop = models.DateTimeField(null=True)
    last_response = models.JSONField(default={}, encoder=DjangoJSONEncoder, null=True, blank=True )
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        db_table = 'scheduler'
        ordering = ['name']

ACTIVITY_ACTION_TYPES = [
    ('POST', 'POST'),
    ('PUT', 'PUT'),
    ('GET', 'GET'),
    ('PATCH', 'PATCH'),
    ('DELETE', 'DELETE')
]
class ActivityLog(models.Model):
    id = models.AutoField(primary_key=True,)
    event_id = models.IntegerField(db_column='event_id', )
    action = models.CharField(
        max_length=10,
        choices=ACTIVITY_ACTION_TYPES,
        default='GET',
        db_column='action',
        db_index=True
    )
    event = models.CharField(max_length=255, db_column='event', null=True,blank=True)
    type = models.CharField( max_length=10,
        choices=ENVIRONMENT_TYPE,
        null=True,
        blank=True,
        db_column='type',
        db_index=True
    )
    user_id = models.ForeignKey(User, to_field='id', db_column='user_id', on_delete=models.CASCADE, db_constraint=True)
    comment = models.CharField(max_length=255, db_column='comment', null=True,blank=True)
    new = models.JSONField(default=None, encoder=DjangoJSONEncoder)
    old = models.JSONField(default=None, encoder=DjangoJSONEncoder)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'activity_log'



# Observers/ Signals
# Signal to reload the project when a snippet is saved
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from BUDjangoProxyApp.services.DynamicLoader import DynamicAppManager


@receiver(post_save, sender=APIInstance)
def reload_api_instance(sender, instance, **kwargs):
    DynamicAppManager.load_api_instance(instance)
    logger.info(f"Reloaded API instance: {instance.api.name} for route: {instance.route}")

@receiver(post_save, sender=APIVersion)
def reload_api_version(sender, instance, **kwargs):
    instances = instance.version_instance.all()
    for api_instance in instances:
        DynamicAppManager.load_api_instance(api_instance)
    logger.info(f"Reloaded all instances for API: {instance.api.name}")


@receiver(pre_save, sender=APIVersion)
def validate_code(sender, instance=None, **kwargs):
    models = helpers.prepare_new_models_file(instance.version_models)
    urls = helpers.prepare_new_url_file(instance.version_urls)
    if instance.version_views is not None and instance.version_views != "":
        views = helpers.prepare_new_views_file(instance.id, instance.version_models,instance.version_views,instance.version_urls)
        helpers.validate_code(views)

    helpers.validate_code(models)

    helpers.validate_code(urls)


EXISTING_TYPES = ["Resource","APIInstance","Environment"]
HIDDEN_FIELDS = ["app_secret","encrypted_app_secret"]

def password_hide(instance_dict):
    if 'resource_type' in instance_dict and instance_dict['resource_type'] =='secret':
        instance_dict['config']['value'] = "***"
    elif 'resource_type' in instance_dict and (instance_dict['resource_type'] =='oracle' or instance_dict['resource_type'] =='mysql'):
        instance_dict['config']['pass'] = "***"
    else:
        for field in instance_dict.keys():
            if field in HIDDEN_FIELDS:
                instance_dict[field] = "***"

    return instance_dict


# @receiver(pre_save, sender=Resource)
def update_activity_logger(sender, instance, **kwargs):
    if sender == ActivityLog:
        return

    request = get_request_context()
    if request.method != "PUT" or request.method != "PATCH":
        return

    try:
        old_instance = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        old_instance = []

    environment_type = None
    if sender.__name__ in EXISTING_TYPES:
        if sender.__name__ == "APIInstance":
            environment_type = instance.environment.type
        elif sender.__name__ == "Environment":
            environment_type = instance.type
        elif sender.__name__ == "Resource":
            environment_type = instance.type

    ActivityLog.objects.create(
        event_id=instance.id,
        event=sender.__name__,
        old=password_hide(model_to_dict(old_instance)) if not isinstance(old_instance, list) else old_instance,
        new=password_hide(model_to_dict(instance)) if instance else [],
        user_id = get_request_user_info(),
        action = request.method,
        type= environment_type
    )

def post_activity_logger(sender, instance, **kwargs):
    if sender == ActivityLog:
        return

    request = get_request_context()
    if request.method != "POST":
        return

    environment_type = None
    if sender.__name__ in EXISTING_TYPES:
        if sender.__name__ == "APIInstance":
            environment_type = instance.environment.type
        elif sender.__name__ == "Environment":
            environment_type = instance.type
        elif sender.__name__ == "Resource":
            environment_type = instance.type

    ActivityLog.objects.create(
        event_id=instance.id,
        event=sender.__name__,
        old=[],
        new=password_hide(model_to_dict(instance)),
        user_id = get_request_user_info(),
        action = request.method,
        type=environment_type
    )

def delete_activity_logger(sender, instance, **kwargs):
    if sender == ActivityLog:
        return

    request = get_request_context()
    if request.method != "DELETE":
        return

    try:
        old_instance = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    environment_type = None
    if sender.__name__ in EXISTING_TYPES:
        if sender.__name__ == "APIInstance":
            environment_type = old_instance.environment.type
        elif sender.__name__ == "Environment":
            environment_type = old_instance.type
        elif sender.__name__ == "Resource":
            environment_type = old_instance.type

    ActivityLog.objects.create(
        event_id=instance.id,
        event=sender.__name__,
        old=password_hide(model_to_dict(old_instance)),
        new=[],
        user_id=get_request_user_info(),
        action=request.method,
        type=environment_type
    )