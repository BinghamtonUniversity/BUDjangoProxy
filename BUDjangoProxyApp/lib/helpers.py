import logging
import json
import os
from django.forms import model_to_dict
from BUDjangoProxyApp.services.LaravelEncryptor import LaravelEncryptor
from BUDjangoProxy.settings import env_values, DYNAMIC_APPS_DIR
import sys
import keyword
from pathlib import Path


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
    except Exception as e:
        raise e


def write_file(path, content):
    """
    Utility function to write content to a file.
    """
    with open(path, "w") as f:
        f.write(content)

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


def db_resource_fix(resource):
    encryptor = LaravelEncryptor(env_values['LARAVEL_APP_KEY'])

    return {
        "name":resource['tns'],
        "user":resource['user'],
        "password":encryptor.decrypt(resource['pass'])
    }

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
        if 'content' not in model or model['content'] is None or model['content'] == '':
            continue

        # Start the model class definition
        appended_models += f"""class {model['name']}({model['inheritance']}):\n"""
        # Add model content with proper indentation
        appended_models += f"""    {model['content'].replace('\n', '\n    ')}\n"""

        # Add Meta class
        appended_models += f"""    class Meta:\n"""
        for meta in model.get('class_meta', []):
            if meta['value'] != "default":
                appended_models += f"""        {meta['name']} = '"{'"."'.join(meta['value'].split(".")).replace('\n', '\n        ')}"'\n"""
        appended_models += "\n"  # Add a newline after Meta

        # Add class methods if they exist
        if 'class_methods' in model:
            for method in model['class_methods']:
                append_str = ""
                if len(method['params'])>0:
                    append_str += f""", {",".join(method['params'])}"""
                if 'content' in method and method['content'] is not None and method['content'] != '':
                    appended_models += f"""    def {method['name']}(self{append_str}):\n"""
                    appended_models += f"""        {method['content'].replace('\n', '\n        ')}\n\n"""

        appended_models += "\n"  # Add a newline between models

    return f"""from django.db import models\n\n{appended_models}"""




def prepare_new_views_file(
    instance_id,
    models,
    views,
    urls,
    files=None,
):
    module_lines = [
        "from django.http import JsonResponse",
        (
            "from BUDjangoProxyApp.services.DynamicLoader "
            "import DynamicAppManager as DataProxyManager"
        ),
        "import importlib",
    ]

    # Import additional developer modules.
    for file in files or []:
        filename = file.get("name", "")

        if not isinstance(filename, str):
            continue

        if not filename.endswith(".py"):
            continue

        module_name = filename[:-3]

        if (
            not module_name.isidentifier()
            or keyword.iskeyword(module_name)
            or module_name in {
                "__init__", "models", "views", "urls"
            }
        ):
            continue

        module_lines.append(
            f"{module_name} = importlib.import_module("
            f"'BUDjangoProxyApp.dynamic_apps."
            f"{instance_id}.{module_name}')"
        )

    module_lines.extend([
        "",
        f"oracledb = DataProxyManager.get_db({instance_id!r})",
        "",
    ])

    # Prepare model initialization statements.
    imported_models = []

    for model in models:
        if not model.get("content"):
            continue

        model_name = model.get("name")

        if model_name:
            imported_models.append(
                f"{model_name} = "
                f"DataProxyManager.get_model({model_name!r})"
            )

    # Generate each view.
    for view in views:
        content = view.get("content")

        if not isinstance(content, str) or not content:
            continue

        view_name = view["name"]

        request_params = next(
            (
                url for url in urls
                if url["view_name"] == view_name
            ),
            None,
        )

        required_params = []

        if request_params:
            required_params = [
                param["name"]
                for param in request_params.get("required", [])
            ]

        request_param = ",".join(required_params)
        extra_params = (
            f",{request_param}" if request_param else ""
        )

        module_lines.append(
            f"def {view_name}"
            f"(request{extra_params}, "
            "args=None, resources=None, options=None):"
        )

        # Hidden model setup lines.
        for model_line in imported_models:
            module_lines.append(f"    {model_line}")

        module_lines.append("")

        # First physical line of developer GUI source.
        gui_start_line = len(module_lines) + 1

        # Preserve GUI line numbering, including blanks.
        for line in content.split("\n"):
            module_lines.append(f"    {line}")

        # Metadata is assigned outside the function.
        module_lines.append("")
        module_lines.append(
            f"{view_name}.__api_gui_start_line__ = "
            f"{gui_start_line}"
        )
        module_lines.append(
            f"{view_name}.__api_gui_source__ = {content!r}"
        )
        module_lines.append("")

    return "\n".join(module_lines) + "\n"



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




RESERVED_DYNAMIC_FILES = {
    "__init__.py",
    "models.py",
    "views.py",
    "urls.py",
}


def prepare_new_additional_files(
    api_version,
    api_instance,
    app_path,
):
    """
    Generate developer helper modules.

    The first two physical lines are infrastructure.
    Developer GUI content begins on physical line 3.
    """

    app_path = Path(app_path).resolve()
    version_files = api_version.version_files or []

    valid_files = []
    seen_names = set()

    for file in version_files:
        if not isinstance(file, dict):
            continue

        filename = file.get("name")
        content = file.get("content")

        if not isinstance(filename, str):
            continue

        if not isinstance(content, str) or not content:
            continue

        # Reject paths and reserved names.
        if (
            Path(filename).name != filename
            or "/" in filename
            or "\\" in filename
            or filename in RESERVED_DYNAMIC_FILES
        ):
            continue

        if not filename.endswith(".py"):
            continue

        module_name = filename[:-3]

        if (
            not module_name.isidentifier()
            or keyword.iskeyword(module_name)
        ):
            continue

        if filename in seen_names:
            raise ValueError(
                f"Duplicate additional filename: {filename}"
            )

        seen_names.add(filename)
        valid_files.append((filename, content))

    # Preserve the original cleanup behavior:
    # retain filenames declared in the API version.
    existing_files = [
        file["name"]
        for file in version_files
        if (
            isinstance(file, dict)
            and isinstance(file.get("name"), str)
        )
    ]

    cleanup_dynamic_app_directory(
        str(app_path),
        existing_files,
    )

    for filename, content in valid_files:

        # Exactly two generated header lines.
        header = (
            "from BUDjangoProxyApp.services.DynamicLoader "
            "import DynamicAppManager as DataProxyManager\n"
            f"oracledb = DataProxyManager.get_db("
            f"{api_instance.id!r})\n"
        )

        generated_source = header + content

        file_path = app_path / filename

        write_file(
            str(file_path),
            generated_source,
        )


def instance_to_dict(instance, with_relations=None):
    data = model_to_dict(instance)
    if with_relations:
        for rel in with_relations:
            related = getattr(instance, rel, None)
            if related is None:
                data[rel] = None
            elif hasattr(related, "all"):  # ManyToMany
                data[rel] = [model_to_dict(r) for r in related.all()]
            else:  # ForeignKey/OneToOne
                data[rel] = model_to_dict(related)
    return data

# Preparing the resources for the
def prepare_instance_resources(resources):
    encryptor = LaravelEncryptor(env_values['LARAVEL_APP_KEY'])
    response_data = {}

    for res in resources['instance_mappings']:
        found_resource = resources['resources'][int(res['resource'])]
        match found_resource['resource_type']:
            case "secret":
                response_data[res['name']] = encryptor.decrypt(found_resource['config']['value'])
            case "value":
                response_data[res['name']] = found_resource['config']['value']
            case "oracle":
                response_data[res['name']] = db_resource_fix(found_resource['config'])
            case "mysql":
                response_data[res['name']] = db_resource_fix(found_resource['config'])
            case "sqlsrv":
                response_data[res['name']] = db_resource_fix(found_resource['config'])
            case _:
                response_data[res['name']] = None

    return response_data

# To clean up all the files that are no longer related to the api_instance
def cleanup_dynamic_app_directory(full_path, allowed_files):
    # Deleting the files/folders for that instance under dynamic_apps directory
    allowed_files += ['__init__.py','apps.py','models.py', 'urls.py','views.py', 'api_version.json']

    if not os.path.exists(full_path):
        print(f"Directory {full_path} does not exist.")
        return

    for filename in os.listdir(full_path):
        file_path = os.path.join(full_path, filename)

        # Only target files, not directories
        if os.path.isfile(file_path) and filename not in allowed_files:
            try:
                os.remove(file_path)
                print(f"Removed: {filename}")
            except Exception as e:
                print(f"Error removing {filename}: {e}")

    return True


def clear_cached_modules(base_prefix):
    for m in list(sys.modules.keys()):
        if m.startswith(base_prefix):
            del sys.modules[m]