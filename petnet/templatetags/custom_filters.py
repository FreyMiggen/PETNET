from django import template

register = template.Library()

@register.filter
def call_method(obj, method_name):
    method = getattr(obj, method_name)
    return method()

@register.filter
def call_method_with_arg(obj, method_and_arg):
    method_name, arg = method_and_arg.split(',')
    method = getattr(obj, method_name)
    return method(arg)