import os
import logging
from operator import truediv

from django.db import models, connection
import json
from django.db.models import JSONField
from django.urls import path, include
from django.conf import settings
from ..models import APIInstance, Resource
import ast
import astor
from ..lib import helpers
from dotenv import dotenv_values
env_values = dotenv_values(".env")

logger = logging.getLogger(__name__)

class DynamicAppManager:
    current_instance_id = None
    instance_model_registry = {}
    instance_view_registry = {}
    instance_url_registry = {}
    instance_settings_registry = {}

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
        print("Writing dynamic app path")

        dynamic_root = os.path.join(settings.BASE_DIR,"BUDjangoProxyApp", "dynamic_apps")
        app_path = os.path.join(dynamic_root, f"{instance_id}")
        os.makedirs(app_path, exist_ok=True)
        return app_path

    @staticmethod
    def write_file(path, content):
        """
        Utility function to write content to a file.
        """
        with open(path, "w") as f:
            f.write(content)

    ### INSTANCE MANAGEMENT ###
    @classmethod
    def create_or_update_app(cls, api_instance):
        """
        Create or update the dynamic app for an API instance.
        """
        app_path = cls.get_app_path(api_instance.id)
        version = api_instance.api_version

        resources_mapping = {
            "resources": {resource['name']: resource for resource in
                          list(Resource.objects.filter(name__in=
                                                       list(api_instance.resources.values())).values())
                          },
            "instance_mappings": api_instance.resources,
            "version_resources": version.resources
        }

        # try:
            # code_content = json.loads(version.code_content)
        # print(version.version_models)
        models_code = (version.version_models['content']) #code_content.get("models", "")

        views_code = helpers.prepare_new_views_file(version.version_views)
        print(views_code)
        urls_code = helpers.prepare_new_url_file(version.version_urls)

        # resources_code = json.loads(version.version_resources)

        # Validate codes
        helpers.validate_code(models_code)
        helpers.validate_code(views_code)
        helpers.validate_code(urls_code)
        # except json.JSONDecodeError as e:
        #     logger.error(f"Failed to decode code_content for APIInstance {api_instance.id}: {e}")
        #     return

        # Write apps to the files first
        cls.write_file(os.path.join(app_path, "__init__.py"), "")  # Ensure it's a Python package
        cls.write_file(os.path.join(app_path, "models.py"), models_code)
        cls.write_file(os.path.join(app_path, "views.py"), views_code)
        cls.write_file(os.path.join(app_path, "urls.py"), urls_code)
        cls.write_file(os.path.join(app_path, "apps.py"), cls.generate_apps_py_content(api_instance.id))

        # Register the models
        cls.register_models(api_instance.id, models_code, resources_mapping)
        cls.register_views(api_instance.id, views_code)
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

        # try:
        exec(models_code, models_namespace)
        for obj_name, obj in models_namespace.items():
            if isinstance(obj, type) and issubclass(obj, models.Model):
                if not hasattr(obj, "_meta"):
                    obj._meta = type("_meta", (), {})

                filtered_resources = {res['model_name']: res['name'] for res in resources_mapping['version_resources']
                                      if res['type'] == 'Model'}
                #     Model DB settings and registration before the model registration
                if obj_name in filtered_resources:

                    version_resource = filtered_resources[obj_name]
                    if version_resource in resources_mapping['instance_mappings']:
                        api_mapping = resources_mapping['instance_mappings'][version_resource]
                        if api_mapping in resources_mapping['resources']:
                            found_resource = resources_mapping['resources'][api_mapping]
                            found_config= helpers.resource_fix(found_resource['config'])
                            print(found_config)
                            settings.DATABASES[api_mapping] = helpers.prepare_new_resource_db(found_resource['resource_type'],found_config)
                            print(settings.DATABASES[api_mapping])
                            obj._meta.db_name= api_mapping

                cls.instance_model_registry[instance_id][obj_name] = obj
                logger.info(f"Registered models for instance {instance_id}")

        # except Exception as e:
        #     logger.error(f"Error registering models for instance {instance_id}: {e}")

    ### VIEW MANAGEMENT ###

    @classmethod
    def register_views(cls, instance_id, views_code):
        """
        Dynamically register views scoped to a specific instance.
        """
        if instance_id not in cls.instance_view_registry:
            cls.instance_view_registry[instance_id] = {}
        views_namespace = {"__name__": f"BUDjangoProxyApp.dynamic_views_{instance_id}"}

        try:
            exec(views_code, views_namespace)
            for obj_name, obj in views_namespace.items():
                if callable(obj):
                    cls.instance_view_registry[instance_id][obj_name] = obj
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
    def get_view(cls, api_instance, view_path):
        """
        Retrieve a specific view for a given route dynamically.
        """
        instance_id = api_instance.id
        instance_views = cls.instance_view_registry.get(instance_id, {})

        found = next(x for x in api_instance.api_version.version_urls if x['path'] == view_path)

        view_func = instance_views.get(found['view_name'])
        cls.current_instance_id = instance_id
        if not view_func:
            raise LookupError(f"View {view_path} not found for instance {api_instance.route}.")

        return view_func


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