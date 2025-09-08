import json
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
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
    username = models.CharField(max_length=11, null=True, blank=True)
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
    description = models.TextField()
    tags = models.CharField(max_length=255, blank=True)
    api_type = models.CharField(max_length=20, default='php', blank=False, null=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE,db_column='user_id')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_created_by')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_updated_by')
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.name} - {self.id}'

    class Meta:
        db_table = "apis"
        ordering = ['name']

class APIVersion(models.Model):
    id = models.AutoField(primary_key=True)
    api = models.ForeignKey(API, on_delete=models.CASCADE, related_name='api_versions',parent_link=True, db_index=True)
    summary = models.CharField(max_length=255, null=True, blank=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    stable = models.BooleanField(default=False)
    version_models = models.JSONField()
    version_views = models.JSONField(db_column='functions', default=list, null=True, blank=True)
    version_urls = models.JSONField(db_column='routes', default=list, null=True, blank=True)
    options = models.JSONField(db_column='options', default=list ,null=True, blank=True)
    version_files = models.JSONField(db_column='files', null=True, blank=True)
    resources = models.JSONField(default=dict, null=True, blank=True)
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_version_created_by', db_column='user_id')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_version_updated_by')

    def __str__(self):
        return f"{self.id} - {self.api.name}"

    class Meta:
        db_table = "api_versions"
        # ordering = ['name']


class APIInstance(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, null=True)
    route = models.CharField(max_length=255, db_column='slug')
    api = models.ForeignKey(API, on_delete=models.CASCADE, related_name='api_instance')
    api_version = models.ForeignKey(APIVersion, default=None, null=True, blank=True, on_delete=models.CASCADE, related_name='version_instance')
    environment = models.ForeignKey(Environment, on_delete=models.CASCADE, db_index=True)
    resources = models.JSONField(encoder=json.JSONEncoder, decoder=json.JSONDecoder, null=True, blank=False)
    options = models.JSONField(encoder=json.JSONEncoder, decoder=json.JSONDecoder, null=True, blank=False)
    route_user_map = models.JSONField(default=list, encoder=json.JSONEncoder, decoder=json.JSONDecoder, db_column='route_user_map', null=True)
    public =models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "api_instances"

    def __str__(self):
        return f"{self.name} ({self.environment.type})"

    def get_instance_version(self):
        if self.api_version is None:
            try:
                return APIVersion.objects.filter(api=self.api).latest('updated_at')
            except APIVersion.DoesNotExist:
                return None
        elif self.api_version == 0:
            try:
                return APIVersion.objects.filter(api=self.api, stable=True).latest('updated_at')
            except APIVersion.DoesNotExist:
                return None
        else:
            return self.api_version

    def get_instance_version_api(self):
        return self.api_version.api


class APIDeveloper(models.Model):
    id = models.AutoField(primary_key=True)
    api_developer = models.ForeignKey(User, max_length=11, db_column='user_id', to_field='id', on_delete=models.CASCADE)
    api = models.ForeignKey(API, max_length=11, db_column='api_id', to_field='id', on_delete=models.CASCADE)

    class Meta:
        unique_together = (('api_developer', 'api'))
        db_table = 'api_developers'

class Resource(models.Model):
    ENVIRONMENT_TYPE = (
        ('dev', 'Development'),
        ('test', 'Testing'),
        ('prod', 'Production'),
    )
    # name = models.CharField(max_length=100)
    RESOURCE_TYPE_CHOICES = [
        ('oracle', 'Oracle'),
        ('mysql', 'MySQL'),
        ('sqlsrv', 'SQL Server'),
        ('secret', 'Secret'),
        ('value', 'Value'),
        ('rest', 'REST'),
    ]
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    resource_type = models.CharField(
        max_length=10,
        choices=RESOURCE_TYPE_CHOICES,
        default='mysql'
    )
    type = models.CharField(
        max_length=10,
        choices=ENVIRONMENT_TYPE,
        default='dev'
    )
    config = models.JSONField(default=None, encoder=DjangoJSONEncoder)

    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f" {self.name}"

    class Meta:
        db_table = 'resources'


class APIUser(models.Model):
    id = models.AutoField(primary_key=True)
    app_name = models.CharField(max_length=255, unique=True, null=False,db_column='app_name',default='api_user')
    app_secret = models.CharField(max_length=255, db_column='app_secret',null=True)  # For storing hashed passwords
    encrypted_app_secret = models.CharField(max_length=255, db_column='encrypted_app_secret',null=True)
    environment = models.ForeignKey(Environment, on_delete=models.CASCADE, db_index=True, null=False,
                                    related_name='environment_users',
                                    default=1)

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
            print(f"Error checking password: {e}")
            return False

    def decrypt_password(self):
        encryption = LaravelEncryptor(env_values['LARAVEL_APP_KEY'])
        return encryption.decrypt(self.encrypted_app_secret)

    def __str__(self):
        return self.app_name

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
    views = helpers.prepare_new_views_file(instance.id,instance.version_views,instance.version_urls)

    helpers.validate_code(models)
    helpers.validate_code(views)
    helpers.validate_code(urls)

    # logger.info(f"Reloaded all instances for API: {version.api.name}")
