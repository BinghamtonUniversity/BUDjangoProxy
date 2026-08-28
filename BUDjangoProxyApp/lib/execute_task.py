from django.http import HttpResponseNotAllowed
from BUDjangoProxyApp.services.CustomPathResolver import CustomPathResolver
from django.utils import timezone
from django.core.management.base import CommandError
from django.test import RequestFactory
import json

# ----------------------------------------------------
# Execute scheduled task
# ----------------------------------------------------
def execute_task(task, loader_instance):
    task.last_exec_cron = timezone.now()
    task.last_exec_start = timezone.now()
    task.save(update_fields=["last_exec_cron", "last_exec_start"])
    response = None
    
    try:
        api_instance = task.api_instance
        if not api_instance:
            raise CommandError("API Instance Not Found")


        factory = RequestFactory()
        if task.verb and task.verb.strip():
            method = task.verb.lower()
        else:
            method = 'get'

        path = f"{api_instance.route}/{task.route}"
        if task.args:
            request = getattr(factory, method)(
                path,
                data={p["name"]: p["value"] for p in task.args},
                HTTP_HOST=api_instance.environment.domain,
                format="json",
            )
        else:
            request = getattr(factory, method)(
                path,
                # data={p["name"]: p["value"] for p in task.args},
                HTTP_HOST=api_instance.environment.domain,
                format="json",
            )

        request.dynamic_app_context = {
            "api_instance": api_instance,
            "environment": api_instance.environment,
            "source": "scheduler",
        }

        # Attach execution metadata
        request.is_scheduled_task = True
        request.scheduler_id = task.id
        if task.args:
            request.data = {p["name"]: p["value"] for p in task.args}


        custom_resolver = CustomPathResolver()
        # Fixing the incoming URL for the URLs file
        custom_resolver.incoming_url_fix(request, api_instance)

        # Get the args and kwargs maps from the resolver
        view_func, args, kwargs = custom_resolver.resolve(request, api_instance)

        version_urls = api_instance.get_instance_version().version_urls
        current_version_url = next((url for url in version_urls if view_func.__name__ == url['view_name']), None)

        if request.method != "ALL" and request.method != current_version_url['verb']:
            task.last_response = {
                "error": f"{request.method} method not allowed for this route",
                "type": "Method Not Allowed",
            }
            task.last_exec_stop = timezone.now()
            task.save(update_fields=["last_response", "last_exec_stop"])

            return HttpResponseNotAllowed(request.method, f"{request.method} method not allowed for this route")


        # Dynamically load and execute the view
        view_func = loader_instance.get_view(api_instance, view_func.__name__)
        response = view_func(request, *args, **kwargs)
        try:
            task.last_response = json.loads(response.content.decode())
        except Exception:
            task.last_response = {"raw": response.decode()}
            raise CommandError(response.decode())

    except Exception as exc:
        task.last_response = {
            "error": str(exc),
            "type": exc.__class__.__name__,
        }
        raise

    finally:
        task.last_exec_stop = timezone.now()
        task.save(update_fields=["last_response", "last_exec_stop"])