import os
import logging
import types
from django.db import models
from django.http import JsonResponse
from django.urls import path, include
from django.conf import settings
from ..models import Resource
import ast
import astor
from ..lib import helpers
from dotenv import dotenv_values
from django.db import connections
from BUDjangoProxyApp.services.OracleDB import OracleDB
import functools

env_values = dotenv_values(".env")

logger = logging.getLogger(__name__)

class DynamicAppManager:
    current_instance_id = None
    instance_model_registry = {}
    instance_view_registry = {}
    instance_url_registry = {}
    instance_db_registry = {}
    instance_options = {}
    instance_resources = {}


    # To Load instances
    @classmethod
    def load_api_instance(cls, api_instance):
        """
        Reload the API instance by creating or updating the app and its components.
        """
        cls.create_or_update_app(api_instance)

    # Reloading all the instances on request
    @classmethod
    def reload_all_instances(cls, version=None):
        """
        Reload all API instances dynamically.
        """
        from BUDjangoProxyApp.models import APIInstance
        instances = APIInstance.objects.select_related('api', 'api_version', 'environment').all()

        for instance in instances:
            try:
                cls.load_api_instance(instance)
            except Exception as e:
                logger.error(e)

        logger.info(f"Reloaded all API instances. Total: {len(instances)}")

    ### UTILITY FUNCTIONS ###
    @staticmethod
    def get_app_path(instance_id):
        """
        Get the path for a dynamic app based on the instance route.
        """

        dynamic_root = os.path.join(settings.BASE_DIR,"BUDjangoProxyApp", "dynamic_apps")
        app_path = os.path.join(dynamic_root, f"{instance_id}")
        os.makedirs(app_path, exist_ok=True)
        return app_path

    @classmethod
    def register_db(cls, instance_id, db_instance):
        cls.instance_db_registry[instance_id] = db_instance


    @classmethod
    def get_db(cls, instance_id):
        return cls.instance_db_registry.get(instance_id)



    ### INSTANCE MANAGEMENT ###
    @classmethod
    def create_or_update_app(cls, api_instance):
        """
        Create or update the dynamic app for an API instance.
        """
        app_path = cls.get_app_path(api_instance.id)
        api_version = api_instance.version_id



        models_code = None

        if not api_version:
            return JsonResponse({"error":"Version does not exist"})

        resources_mapping = {
            "resources": {resource['id']: resource for resource in
                          list(Resource.objects.
                               filter(id__in=[int(res['resource'])
                                              for res in api_instance.resources
                                              if 'resource' in res]).values())
                          } if api_instance.resources else {},
            "instance_mappings": api_instance.resources,
            "version_resources": api_version.resources
        }

        # try:
            # code_content = json.loads(version.code_content)
        # Prepare the version files
        if len(api_version.version_models)>0:
            models_code = helpers.prepare_new_models_file(api_version.version_models) #code_content.get("models", "")

        if resources_mapping['instance_mappings'] is not None:
            class_config = OracleDB()
            try:
                for db in resources_mapping['instance_mappings']:
                    found_db_resource = resources_mapping['resources'][int(db['resource'])]
                    if found_db_resource['resource_type'] != 'secret' and found_db_resource['resource_type'] != 'value':
                        found_config = helpers.db_resource_fix(found_db_resource['config'])
                        ready_config = helpers.prepare_new_resource_db(found_db_resource['resource_type'], found_config)
                        class_config.config_database(db['name'], ready_config)

                cls.register_db(api_instance.id, class_config)
            except Exception as e:
                logger.error(e)

        # Create new additional files
        helpers.prepare_new_additional_files(api_version, api_instance, app_path)

        if api_version.version_views != "" and api_version.version_views is not None:
            views_code = helpers.prepare_new_views_file(api_instance.id,
                                                        api_version.version_models,
                                                        api_version.version_views,
                                                        api_version.version_urls,
                                                        files=api_version.version_files)
            helpers.validate_code(views_code)

        if api_version.version_urls != "" and api_version.version_urls is not None:
            urls_code = helpers.prepare_new_url_file(api_version.version_urls)
            helpers.validate_code(urls_code)

        # Validate codes
        if models_code:
            helpers.validate_code(models_code)

        # except json.JSONDecodeError as e:
        #     logger.error(f"Failed to decode code_content for APIInstance {api_instance.id}: {e}")
        #     return

        # Write apps to the files first
        helpers.write_file(os.path.join(app_path, "__init__.py"), "")  # Ensure it's a Python package
        if models_code:
            helpers.write_file(os.path.join(app_path, "models.py"), models_code)

        helpers.write_file(os.path.join(app_path, "views.py"), views_code)
        helpers.write_file(os.path.join(app_path, "urls.py"), urls_code)
        helpers.write_file(os.path.join(app_path, "apps.py"), cls.generate_apps_py_content(api_instance.id))

        # Register the models/views/urls
        if models_code:
            cls.register_models(api_instance.id, models_code, resources_mapping)


        if views_code:
            cls.register_views(api_instance.id, views_code,
                               resources= helpers.prepare_instance_resources(resources_mapping),
                               options=api_instance.options
                               )
        if urls_code:
            cls.register_urls(api_instance.id, urls_code)

    @classmethod
    def generate_apps_py_content(cls, instance_id):
        """
        Generate the content for the apps.py file for a dynamic app.
        """
        return f"""
from django.apps import AppConfig

class Instance{instance_id}Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'BUDjangoProxyApp.dynamic_apps.{instance_id}'
    app_label = f'dynamic_apps.{instance_id}'
    """

    ### MODEL MANAGEMENT ###

    @classmethod
    def register_models(cls, instance_id, models_code, resources_mapping):
        """
        Dynamically register models scoped to a specific instance.
        """
        app_label = f"BUDjangoProxyApp.dynamic_apps_{instance_id}"

        models_code = cls.modify_all_model_definitions(models_code,app_label)

        if instance_id not in cls.instance_model_registry:
            cls.instance_model_registry[instance_id] = {}

        models_namespace = {
            "models": models,
            "__name__": f"BUDjangoProxyApp.dynamic_models_{instance_id}",
            "app_label": f"dynamic_apps_{instance_id}"
        }

        try:
            exec(models_code, models_namespace)
            for obj_name, obj in models_namespace.items():
                if isinstance(obj, type) and issubclass(obj, models.Model):
                    if not hasattr(obj, "_meta"):
                        obj._meta = type("_meta", (), {})

                    if not resources_mapping['resources']:
                        return

                    filtered_resources = {res['model_name']: res['name'] for res in resources_mapping['version_resources']
                                          if res['type'] == 'Model'}

                    # Model DB settings and registration before the model registration
                    if obj_name in filtered_resources:
                        version_resource = filtered_resources[obj_name]
                        api_mapping = next((e for e in resources_mapping['instance_mappings'] if e['name'] == version_resource), None)
                        if api_mapping:
                            if int(api_mapping['resource']) in resources_mapping['resources']:
                                found_resource = resources_mapping['resources'][int(api_mapping['resource'])]
                                found_config = helpers.db_resource_fix(found_resource['config'])
                                if api_mapping['name'] != 'default':
                                    db_config = helpers.prepare_new_resource_db(found_resource['resource_type'],found_config)
                                    db_alias = f"{api_mapping['name']}_{instance_id}"

                                    obj._meta.db_alias = db_alias
                                    obj._meta.db_config = db_config

                                    if db_alias not in connections.databases:
                                        connections.databases[db_alias] = db_config

                                obj._meta.db_name = db_alias

                    cls.instance_model_registry[instance_id][obj_name] = obj
                    logger.info(f"Registered models for instance {instance_id}")

        except Exception as e:
            raise Exception(f"Failed to register models for instance {instance_id}: {e}")

    ### VIEW MANAGEMENT ###

    @classmethod
    def register_views(cls, instance_id, views_code, resources, options):
        """
        Dynamically register views scoped to a specific instance.
        """
        if instance_id not in cls.instance_view_registry:
            cls.instance_view_registry[instance_id] = {}
        views_namespace = {"__name__": f"BUDjangoProxyApp.dynamic_views_{instance_id}"}

        try:
            exec(views_code, views_namespace)
            for obj_name, obj in views_namespace.items():
                if callable(obj) and isinstance(obj, types.FunctionType):
                    def make_wrapper(func, _resources=resources, _options=options):
                        @functools.wraps(func)
                        def wrapper(request, *view_args, **view_kwargs):

                            # Make external args/resources/options available to the view
                            view_kwargs['args']= request.data
                            view_kwargs['resources'] = _resources
                            view_kwargs['options'] = _options
                            return func(request, *view_args, **view_kwargs)

                        return wrapper

                    wrapped = make_wrapper(obj)
                    cls.instance_view_registry[instance_id][obj_name] = wrapped

                    logger.info(f"View {obj_name} registered for instance {instance_id}")
        except Exception as e:
            logger.error(f"Error registering views for instance {instance_id}: {e}")

    ### URL MANAGEMENT ###

    @classmethod
    def register_urls(cls, instance_id, urls_code):
        """
        Dynamically register URLs scoped to a specific instance.
        """
        if instance_id not in cls.instance_url_registry:
            cls.instance_url_registry[instance_id] = []

        # Inject registered views into the namespace
        views_namespace = cls.instance_view_registry.get(instance_id, {})

        urls_namespace = {
            "__name__": f"BUDjangoProxyApp.dynamic_urls_{instance_id}",
            "path": path,
            "__package__": f"BUDjangoProxyApp.dynamic_apps.{instance_id}",  # Set the correct package context
            "include": include,
            "urlpatterns": [],
            **views_namespace,  # Merge views into the namespace
        }

        try:
            exec(urls_code, urls_namespace)
            cls.instance_url_registry[instance_id] = urls_namespace["urlpatterns"]
            logger.info(f"URLs registered for instance {instance_id}")
        except ImportError as e:
            logger.error(f"Error in URLs for instance {instance_id}: {e}")
        except Exception as e:
            logger.error(f"Error registering URLs for instance {instance_id}: {e}")


    ### ACCESSORS ###
    @classmethod
    def get_view(cls, api_instance, view_name):
        """
        Retrieve a specific view for a given route dynamically.
        """
        instance_id = api_instance.id
        instance_views = cls.instance_view_registry.get(instance_id, {})
        api_version = api_instance.get_instance_version()

        if not api_version:
            return JsonResponse({"error": "Version does not exist"})

        view_func = instance_views.get(view_name)
        cls.current_instance_id = instance_id
        if not view_func:
            raise LookupError(f"View {view_name} not found for instance {api_instance.route}.")
        try:
            return view_func
        except Exception as e:
            raise Exception(e)


    @classmethod
    def get_model(cls, model_name):
        try:
            # Retrieve the model from Django's app registry
            model = cls.instance_model_registry[cls.current_instance_id][model_name]
            return model
        except LookupError as e:
            logger.error(f"Model '{model_name}' not found in app '{model_name}': {e}")
            raise LookupError(f"Model '{model_name}' not found or registered'.")


    ### Updating the model definitions ###
    @classmethod
    def modify_all_model_definitions(cls, model_def_str, enforced_app_label):
        """
        Modifies all model definitions in the input string to add or enforce app_label in the Meta class.

        :param model_def_str: Original string containing multiple model definitions.
        :param enforced_app_label: The app_label string to enforce.
        :return: Modified model definition string.
        """
        # Parse the model definition string into an AST
        tree = ast.parse(model_def_str)

        # Iterate through all class definitions
        for class_node in [node for node in tree.body if isinstance(node, ast.ClassDef)]:
            # Check if it's a Django model (inherits from models.Model)
            if any(isinstance(base, ast.Attribute) and base.attr == "Model" for base in class_node.bases):
                # Find the Meta class within the model
                meta_class_node = next(
                    (node for node in class_node.body if isinstance(node, ast.ClassDef) and node.name == "Meta"), None)

                if meta_class_node:
                    # Check if app_label is already defined
                    app_label_node = next((node for node in meta_class_node.body if
                                           isinstance(node, ast.Assign) and node.targets[0].id == "app_label"), None)
                    if app_label_node:
                        # Enforce the app_label value
                        app_label_node.value = ast.Constant(value=enforced_app_label)
                    else:
                        # Add app_label to the existing Meta class
                        meta_class_node.body.append(ast.Assign(
                            targets=[ast.Name(id="app_label", ctx=ast.Store())],
                            value=ast.Constant(value=enforced_app_label)
                        ))
                else:
                    # Create a Meta class with app_label and add it to the model
                    meta_class_node = ast.ClassDef(
                        name="Meta",
                        bases=[],
                        keywords=[],
                        body=[
                            ast.Assign(
                                targets=[ast.Name(id="app_label", ctx=ast.Store())],
                                value=ast.Constant(value=enforced_app_label)
                            )
                        ],
                        decorator_list=[]
                    )
                    class_node.body.append(meta_class_node)

        # Convert the modified AST back to a string
        return astor.to_source(tree)

