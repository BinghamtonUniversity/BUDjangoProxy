import importlib
import json
import sys

from django.urls.resolvers import get_resolver, RegexPattern
from django.urls import resolve, Resolver404, include, path, URLResolver


class CustomPathResolver:
    def incoming_url_fix(self, request, api_instance):
        args_dict = request.GET.dict()
        args_dict.update(request.POST.dict())
        if request.method == "POST" and request.content_type == 'application/json':
            args_dict.update(json.loads(request.body))

        if len(args_dict)>0:
            request.args = args_dict
            instance_version = api_instance.get_instance_version()
            if instance_version:
                found_required_params = next((url['required'] for url in instance_version.version_urls if url['path'] in request.path and 'required' in url), None)
                if found_required_params:
                    request.path += "/"
                    request.path += "/".join([args_dict[param['name']] for param in found_required_params if param['name'] in args_dict])


    def resolve(self, request, api_instance, refresh_required=False):
        instance_id = api_instance.id  # Assuming APIInstance has an 'id' field
        base_prefix = f"BUDjangoProxyApp.dynamic_apps.{instance_id}"
        module_path = f"{base_prefix}.urls"

        def clear_cached_modules():
            for m in list(sys.modules.keys()):
                if m.startswith(base_prefix):
                    del sys.modules[m]

        # Check if the module is already loaded and reload it to pick up changes
        if refresh_required:
            clear_cached_modules()

        try:
            # Try loading fresh module (may be cached if no refresh)
            urls_module = importlib.import_module(module_path)
        except Exception:
            # IF IMPORT FAILS → clear cache and re-import
            clear_cached_modules()
            urls_module = importlib.import_module(module_path)

        # instance_version = api_instance.get_instance_version()

        # Get the URL patterns from the module
        dynamic_urlconf = getattr(urls_module, 'urlpatterns', [])

        # Validate url_patterns
        if not isinstance(dynamic_urlconf, list):
            raise ValueError(f"Expected urlpatterns to be a list, got {type(dynamic_urlconf)}")
        for pattern in dynamic_urlconf:
            if not hasattr(pattern, 'callback') or not callable(pattern.callback):
                raise ValueError(f"Invalid URL pattern: {pattern} (missing or invalid callback)")


        request_path = request.path.strip('/').split('/')

        # Create a URLResolver directly with the dynamic patterns
        resolver = URLResolver(RegexPattern(r'^/'), urlconf_name=dynamic_urlconf)

        print("resolver", resolver)

        # Rewrite the request path to match the dynamic URL patterns
        adjusted_path = '//'+'/'.join(request_path[1:]) + ('/' if request.path.endswith('/') else '')
        request.path_info = adjusted_path
        print(f"Adjusted path: {adjusted_path}")

        resolver_match = resolver.resolve(adjusted_path)

        view_func = resolver_match.func
        args = resolver_match.args
        kwargs = resolver_match.kwargs
        request.data.update(dict(kwargs))
        # print(f"View function Name: {view_func.__name__}, args: {args}, kwargs: {kwargs}")


        # Call the view function through the resolver
        return view_func, args, kwargs