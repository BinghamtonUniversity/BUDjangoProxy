import logging
import json
from BUDjangoProxyApp.services.LaravelEncryptor import LaravelEncryptor
from BUDjangoProxy.settings import env_values, DYNAMIC_APPS_DIR

logger = logging.getLogger(__name__)

def load_into_dict(file_name):
    f = open(file_name)
    data = json.load(f)
    return data

def save_result_file(out_file, data):
    try:
        with open(out_file, 'w') as file:
            file.write(json.dumps(data))
            file.close()
            print(out_file + " has been saved with: " + str(len(data))+ " records!")
    except Exception as e:
            print(f"Failed to save errors to {out_file}: {e}")

def validate_code(code, code_type="python", context_lines=2):
    """
    Validate the provided Python code for syntax errors and log the line number with surrounding context.

    Args:
        code (str): The Python code to validate.
        code_type (str): The type of code (for logging purposes, e.g., 'models_code').
        context_lines (int): Number of lines to display before and after the error.
    Returns:
        bool: True if the code is valid, False otherwise.
    """
    if code_type == "python":
        try:
            compile(code, '<string>', 'exec')  # Attempt to compile the code
            return True
        except SyntaxError as e:
            # Split code into lines for better context
            lines = code.splitlines()
            error_line_index = e.lineno - 1  # Zero-based index for the error line

            # Get surrounding context lines
            start = max(0, error_line_index - context_lines)
            end = min(len(lines), error_line_index + context_lines + 1)
            context = "\n".join(
                f"{i + 1:>4}: {line}" + ("  <--- ERROR" if i == error_line_index - 1 else "")
                for i, line in enumerate(lines[start:end])
            )

            # Log the error with context
            error_message = (
                f"Syntax error in {code_type}:\n"
                f"  Message: {e.msg}\n"
                f"  Line: {e.lineno}\n"
                f"  Offset: {e.offset}\n"
                f"  Code Context:\n{context}"
            )
            logger.error(error_message)
            raise SyntaxError(error_message)


def prepare_new_resource_db(type, resource):
    match type:
        case "oracle":
            return  {
                'ATOMIC_REQUESTS': False,
                'AUTOCOMMIT': True,
                'CONN_HEALTH_CHECKS': False,
                'CONN_MAX_AGE': 0,
                'ENGINE': 'django.db.backends.oracle',
                'NAME': resource['name'],
                'USER': resource['user'],
                'PASSWORD': resource['password'],
                'OPTIONS': {},
                'PORT': None,
                'TEST': {
                    'CHARSET': None,
                         'COLLATION': None,
                         'MIGRATE': True,
                         'MIRROR': None,
                         'NAME': None
                },
                'TIME_ZONE': None
            }
        case "mysql":
            return {
                'ATOMIC_REQUESTS': False,
                'AUTOCOMMIT': True,
                'CONN_HEALTH_CHECKS': False,
                'CONN_MAX_AGE': 0,
                'ENGINE': 'django.db.backends.mysql',
                'NAME': resource['name'],
                'USER': resource['user'],
                'PASSWORD': resource['password'],
                'OPTIONS': {},
                'PORT': None,
                'TEST': {'CHARSET': None,
                         'COLLATION': None,
                         'MIGRATE': True,
                         'MIRROR': None,
                         'NAME': None},
                'TIME_ZONE': None
            }


def prepare_new_models_file(models):
    appended_models = ""

    for model in models:
        # Start the model class definition
        appended_models += f"""class {model['name']}({model['inheritance']}):\n"""
        # Add model content with proper indentation
        appended_models += f"""    {model['content'].replace('\n', '\n    ')}\n"""

        # Add Meta class
        appended_models += f"""    class Meta:\n"""
        for meta in model.get('class_meta', []):
            if meta['value'] != "default":
                appended_models += f"""        {meta['name']} = '{meta['value'].replace('\n', '\n        ')}'\n"""
        appended_models += "\n"  # Add a newline after Meta

        # Add class methods if they exist
        if 'class_methods' in model:
            for method in model['class_methods']:
                appended_models += f"""    def {method['name']}({method['params']}):\n"""
                appended_models += f"""        {method['content'].replace('\n', '\n        ')}\n\n"""

        appended_models += "\n"  # Add a newline between models

    return f"""from django.db import models\n\n{appended_models}"""


def prepare_new_views_file(instance_id,views, urls,files=None, resources=None, options=None):
    appended_views = ""
    for view in views:
        request_param = ""
        request_params = next((url for url in urls if url['view_name'] == view['name']), None)
        if 'required' in request_params and len(request_params['required'])>0:
            required_params = [param['name'] for param in request_params['required']]
            request_param = ",".join(required_params)

        appended_views += f"""def {view['name']}(request{","+request_param if request_param!="" else ''}):
    args = request.args if hasattr(request,'args') else None
    options = {options if options is not None else 'None'}
    resources = {resources if resources is not None else 'None'}
    
    {view['content'].replace('\n', '\n    ')}
"""
    appended_files = ""
    if files is not None:
        for file in files:
            appended_files += f"""{file['name'].split(".")[0]} = importlib.import_module("BUDjangoProxyApp.dynamic_apps.{instance_id}.{file['name'].split(".")[0]}")\n"""

    return f"""from django.http import JsonResponse
from BUDjangoProxyApp.services.DynamicLoader import DynamicAppManager as DataProxyManager
import importlib
{appended_files}
oracledb = DataProxyManager.get_db({instance_id})
{appended_views}
"""

# Preparing the urls files
def prepare_new_url_file(urls):
    url_patterns = []


    for url in urls:
        request_param = ""
        if url and 'required' in url:
            required_params = [f"<str:{param['name']}>" for param in url['required']]
            request_param = "/".join(required_params)

        url_patterns.append(f"path('{url['path']}{"/"+request_param if request_param != "" else ""}',view={url['view_name']},name='{url['view_name']}')")


    return f"""
from django.urls import path
from .views import *

urlpatterns = [{",\n".join(url_patterns)}]
    """

def resource_fix(resource):
    encryptor = LaravelEncryptor(env_values['LARAVEL_APP_KEY'])

    return {
        "name":resource['tns'],
        "user":resource['user'],
        "password":encryptor.decrypt(resource['pass'])
    }