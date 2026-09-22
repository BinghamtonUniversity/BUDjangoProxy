from functools import wraps

from django.http import JsonResponse


def policy(check_func, object_arg_name=None):
    """
    check_func: a function(request, object_id) -> (bool, object|JsonResponse)
    object_arg_name: the kwarg name in the URL (default "id")
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            object_id = kwargs.get(object_arg_name)
            if object_id is None:
                allowed = check_func(request)
            else:
                allowed, result = check_func(request, object_id)

            if not allowed:
                return JsonResponse({"error": "Not authorized for this action"}, status=403)
            # attach object for the view
            if object_id is not None:
                request.policy_object = result

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator