import logging

from BUDjangoProxyApp.services.LaravelEncryptor import LaravelEncryptor
from BUDjangoProxy.settings import env_values
import os
# from django.conf import settings

# from django.urls import path

logger = logging.getLogger(__name__)

def validate_code(code, code_type="Python code", context_lines=2):
    """
    Validate the provided Python code for syntax errors and log the line number with surrounding context.

    Args:
        code (str): The Python code to validate.
        code_type (str): The type of code (for logging purposes, e.g., 'models_code').
        context_lines (int): Number of lines to display before and after the error.
    Returns:
        bool: True if the code is valid, False otherwise.
    """

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


def prepare_new_url_file(urls):
    # print(type(urls))
    url_patterns = []
    for url in urls:
        url_patterns.append(f"path('{url['path']}',view={url['view_name']},name='{url['view_name']}')")


    return f"""
from django.urls import path
from .views import *

urlpatterns = [{",\n".join(url_patterns)}]
    """

def prepare_new_views_file(views):
    appended_views = ""
    for view in views:
        appended_views += f"""def {view['name']}(request):
    {view['content'].replace('\n', '\n    ')}
"""

    return f"""from django.http import JsonResponse
from BUDjangoProxyApp.services.dynamic_loader import DynamicAppManager as DataProxyManager
{appended_views}
"""

def prepare_new_models_file(models):
    appended_models = f"""{models['content']}""" if 'content' in models else ""
    # appended_models = ""
    # for model in models:
    #     appended_models += f"""
    #     def {model['name']}(request):
    #         \t\t{model['content']}
    #     """
    return f"""
from django.db import models\n\n
{appended_models}
"""


def resource_fix(resource):
    encryptor = LaravelEncryptor(env_values['LARAVEL_APP_KEY'])

    return {
        "name":resource['tns'],
        "user":resource['user'],
        "password":encryptor.decrypt(resource['pass'])
    }