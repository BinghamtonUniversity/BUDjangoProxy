from contextvars import ContextVar

request_user_info = ContextVar("request_user_info", default=None)
request_context = ContextVar("request", default=None)

def set_request_user_info(value):
    request_user_info.set(value)

def get_request_user_info():
    return request_user_info.get()

def set_request_context(value):
    request_context.set(value)

def get_request_context():
    return request_context.get()