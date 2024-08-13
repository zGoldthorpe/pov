"""
POV module

Glorified printing functionality and low-budget debugging.
"""

from os import environ as _env

if _env.get("POV_DISABLE", "0").lower() in ["0", "false"] or _env.get("POV_FILE") is not None:
    from ._impl import (
        POV,
        intercept,
        init as __init__,
    )
    __init__(ignore_frames=(__file__,))
else:
    from ._stub import (
        POV,
        intercept,
    )

class __POVIdForwarder:

    def __init__(self, func):
        def forward_func(id):
            def partial_eval(*args, **kwargs):
                return func(*args, **kwargs, __pov_id=id)
            return partial_eval
        self._func = forward_func
    
    def __getitem__(self, id:int):
        return self._func(id)
    
    def __call__(self, *args, **kwargs):
        return self._func(0)(*args, **kwargs)

def print_to(file):
    """
    Change output destination (defaults to sys.stderr)
    """
    return POV().print_to(file)

@__POVIdForwarder
def detail(depth, *, full=None, globally=False, __pov_id):
    """
    Control level of detail of printed values.
    depth:  -1 for unlimited depth (warning: there are no guards against recursion in this case!)
    full:   probe private attributes as well
    """
    return POV().detail[__pov_id](depth, full=full, globally=globally)

@__POVIdForwarder
def info(*args, __pov_id, **kwargs):
    """
    Simple logger; behaves like an ordinary print.
    """
    return POV().info[__pov_id](*args, **kwargs)

@__POVIdForwarder
def ok(*args, __pov_id, **kwargs):
    """
    Log an 'ok' event; behaves like an ordinary print.
    """
    return POV().ok[__pov_id](*args, **kwargs)

@__POVIdForwarder
def bad(*args, __pov_id, **kwargs):
    """
    Log a 'bad' event; behaves like an ordinary print.
    """
    return POV().bad[__pov_id](*args, **kwargs)

@__POVIdForwarder
def warn(*args, __pov_id, **kwargs):
    """
    Log a warning; behaves like an ordinary print.
    """
    return POV().warn[__pov_id](*args, **kwargs)

@__POVIdForwarder
def view(*exprs:str, view_title:str=None, __pov_id, **kwexprs:str):
    """
    View the value of various expressions.
    """
    return POV().view[__pov_id](*exprs, view_title=view_title, **kwexprs)

@__POVIdForwarder
def check(*exprs:str, exit_on_failure=False, interact_on_failure=False, __pov_id):
    """
    Check if expressions evaluate (or cast) to True.
    """
    return POV().check[__pov_id](*exprs, exit_on_failure=exit_on_failure, interact_on_failure=interact_on_failure)

@__POVIdForwarder
def interact(*, normal_exit=False, normal_quit=True, __pov_id):
    """
    Spawn an interactive session within the current context
    """
    return POV().interact[__pov_id](normal_exit=normal_exit, normal_quit=normal_quit)

@__POVIdForwarder
def track_attr(obj, *attrs:str, __pov_id):
    """
    Track all modifications of a class or object's attrs.
    Use `all` (the built-in function) as value to track all attributes (i.e., attrs=all);
    otherwise, attributes should be strings.
    """
    return POV().track_attr[__pov_id](obj, *attrs)

@__POVIdForwarder
def track_memfun(obj, function:str, *, __pov_id):
    """
    Track member function calls
    """
    return POV().track_memfun[__pov_id](obj, function)

@__POVIdForwarder
def track(target=None, *, name=None, attrs=(), __pov_id):
    """
    Decorator wrapping functions and classes to enable tracking
    attrs:  a tuple or list of strings / the builtin `all` indicating which attributes
            to track (cf. track_attr)
    """
    return POV().track[__pov_id](target, name=name, attrs=attrs)

@__POVIdForwarder
def nop(expr, *, __pov_id, **notes):
    """
    Logged "nop". Keywords get printed in the logger as well.
    Always returns eval(expr) in the ambient context.

    One use case is to tweak a function argument, while retaining the original:
    __import__("pov").nop(<new_arg>, old=<old_arg>)
    """
    return POV().nop[__pov_id](expr, **notes)