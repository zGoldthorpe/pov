"""
Stub version of POV module
Does nothing
"""

class POV:

    def __init__(self, *_, **__):
        pass

    def __call__(self, *_, **__):
        return self

    def __getattribute__(self, attr):
        if attr == "nop":
            return lambda x, *_, **__: x
        return self
    
    def __getitem__(self, _):
        return self

class _IdCallable:

    def __init__(self, func):
        self._func = func

    def __getitem__(self, _):
        return self
    
    def __call__(self, *args, **kwargs):
        return self._func(*args, **kwargs)

@_IdCallable
def intercept(target, *_, **__):
    return target

def sanitise(target):
    return target

def sanitise_inputs(func):
    return func