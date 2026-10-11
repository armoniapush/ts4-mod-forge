# -*- coding: utf-8 -*-
import functools

def inject(target_object, target_function_name):
    """
    Decorador para inyección en tiempo de ejecución de Maxis.
    Preserva metadatos originales (__name__, __doc__, __module__).
    """
    def _wrap(new_function):
        if hasattr(target_object, target_function_name):
            original_function = getattr(target_object, target_function_name)

            @functools.wraps(original_function)
            def _injected(*args, **kwargs):
                return new_function(original_function, *args, **kwargs)

            setattr(target_object, target_function_name, _injected)
        return new_function
    return _wrap
