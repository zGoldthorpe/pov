"""
POV module

Glorified printing functionality and low-budget debugging.
"""

from os import environ as _env

if _env.get("POV_DISABLE", "0").lower() in ["0", "false"]:
    from ._impl import (
        POV,
        POVDict,
        POVList,
        init as __init__,
    )
    __init__(ignore_frames=(__file__,))
else:
    from ._stub import (
        POV,
        POVDict,
        POVList,
    )

def print_to(file):
    """
    Change output destination (defaults to sys.stderr)
    """
    return POV().print_to(file)

def detail(depth, *, full=None, globally=False):
    """
    Control level of detail of printed values.
    depth:  -1 for unlimited depth (warning: there are no guards against recursion in this case!)
    full:   probe private attributes as well
    """
    return POV().detail(depth, full=full, globally=globally)

def info(*args, **kwargs):
    """
    Simple logger; behaves like an ordinary print.
    """
    return POV().info(*args, **kwargs)

def ok(*args, **kwargs):
    """
    Log an 'ok' event; behaves like an ordinary print.
    """
    return POV().ok(*args, **kwargs)

def bad(*args, **kwargs):
    """
    Log a 'bad' event; behaves like an ordinary print.
    """
    return POV().bad(*args, **kwargs)

def warn(*args, **kwargs):
    """
    Log a warning; behaves like an ordinary print.
    """
    return POV().warn(*args, **kwargs)

def view(*exprs:str, view_title:str=None, **kwexprs:str):
    """
    View the value of various expressions.
    """
    return POV().view(*exprs, view_title=view_title, **kwexprs)

def check(*exprs:str, exit_on_failure=False, interact_on_failure=False):
    """
    Check if expressions evaluate (or cast) to True.
    """
    return POV().check(*exprs, exit_on_failure=exit_on_failure, interact_on_failure=interact_on_failure)

def interact(normal_exit=False, normal_quit=True):
    """
    Spawn an interactive session within the current context
    """
    return POV().interact(normal_exit=normal_exit, normal_quit=normal_quit)

def track_attr(obj, *attrs:str):
    """
    Track all modifications of a class or object's attrs.
    Use `all` (the built-in function) as value to track all attributes (i.e., attrs=all);
    otherwise, attributes should be strings.
    """
    return POV().track_attr(obj, *attrs)

def track_memfun(obj, function:str):
    """
    Track member function calls
    """
    return POV().track_memfun(obj, function)

def track(target=None, *, name=None, attrs=()):
    """
    Decorator wrapping functions and classes to enable tracking
    attrs:  a tuple or list of strings / the builtin `all` indicating which attributes
            to track (cf. track_attr)
    """
    return POV().track(target, name=name, attrs=attrs)

def nop(expr, **notes):
    """
    Logged "nop". Keywords get printed in the logger as well.
    Always returns eval(expr) in the ambient context.

    One use case is to tweak a function argument, while retaining the original:
    __import__("pov").nop(<new_arg>, old=<old_arg>)
    """
    return POV().nop(expr, **notes)