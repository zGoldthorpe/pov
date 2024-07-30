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
    
class POVDict(dict):

    def __init__(self, *args, pov_name=None, **kwargs):
        dict.__init__(self, *args, **kwargs)

class POVList(list):

    def __init__(self, *args, pov_name=None, **kwargs):
        list.__init__(self, *args, **kwargs)