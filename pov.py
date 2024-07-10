"""
POV module

Glorified printing functionality
"""

import code
import inspect
import sys

_global_stacklimit=1
_global_file=sys.stderr

class POV:

    def __init__(self, *, stacklimit=-1, file=None, _pov_depth=0):
        """
        Initialisation parameters:
        stacklimit: how many levels of stack context to print (None for no limit)
                    (default: 1)
        file:       print output file
                    (default: stderr)
        """
        if stacklimit == -1:
            stacklimit = _global_stacklimit
        if file is None:
            file = _global_file
        
        self._stack = inspect.stack()[_pov_depth+1:]
        self._stacklimit = stacklimit
        self._file = file
        stackrange = range(stacklimit if stacklimit else len(self._stack))
        self._log = []
        for frame, _ in reversed(list(zip(self._stack, stackrange))):
            self._print("[/]", f"{frame.filename}:{frame.lineno} ({frame.function})")
    
    def flush(self):
        """
        Flush output
        """
        for args, kwargs in self._log:
            kwargs["file"] = self._file
            print(*args, **kwargs)
        self._log.clear()

        return self
    
    def __del__(self):
        self.flush()

    def _print(self, *args, **kwargs):
        self._log.append((args, kwargs))

    def _get_context(self):
        frame = self._stack[0].frame
        return dict(frame.f_locals, **frame.f_globals)

    def log(self, *args, **kwargs):
        """
        Simple logger; behaves like an ordinary print.
        """
        self._print("[i]", *args, **kwargs)
        return self
    
    def view(self, *exprs : str):
        """
        View the value of various expressions.
        """

        context = self._get_context()
        
        for expr in exprs:
            if not isinstance(expr, str):
                self._print("[+]", expr, sep='\t')
                continue
            try:
                val = eval(expr, context)
                self._print(f"[+]\t{expr}", "=>", val, "::", type(val).__name__)
            except Exception as e:
                self._print(f"[-]\t{expr}", "><", type(e).__name__, "::", e)

        return self

    def interact(self, normal_exit=False, normal_quit=True):
        """
        Spawn an interactive session within the current context
        """
        context = self._get_context()
        ctrl = 'Z' if sys.platform == "win32" else 'D'
        close_msg = f"Press Ctrl-{ctrl} to close interactive mode and continue."
        exit_cmds = []
        if normal_exit:
            exit_cmds.append("call exit()")
        if normal_quit:
            exit_cmds.append("call quit()")
        if len(exit_cmds) == 0:
            exit_cmds.append("raise SystemExit")
        exit_msg = f"To terminate program, {' or '.join(exit_cmds)}"
        
        msg = f"{close_msg}\n{exit_msg}"
        if not normal_exit:
            context["exit"] = lambda *_: print(msg)
        if not normal_quit:
            context["quit"] = lambda *_: print(msg)
        
        code.interact(banner=f"[i] Entering interactive mode.\n{msg}", local=context, exitmsg="[i] Resuming normal execution...")

        return self

    def track_attr(self, obj:type|object, *attrs:str, all_attrs=False):
        """
        Track all modifications of a class or object's attrs.
        """
        cls = obj if isinstance(obj, type) else type(obj)
        old_setattr = cls.__setattr__
        self._print("Tracking", "all attrs" if all_attrs else ", ".join(attrs),
                    "for", cls.__name__, f"object {hex(id(obj))}" if not isinstance(obj, type) else "objects")

        def _pov_new_setattr(_self, _attr, _value):
            depth = 0
            for frame in inspect.stack():
                if frame.function.startswith("_pov"):
                    depth += 1
                else:
                    break

            if (all_attrs or _attr in attrs) and (isinstance(obj, type) or _self == obj):
                POV(stacklimit=self._stacklimit,
                    file=self._file,
                    _pov_depth=depth)._print(
                        f"[a]\t{cls.__name__}.{_attr}", ":=", _value,
                        "::", f"[{hex(id(_self))}]")
            return old_setattr(_self, _attr, _value)
        
        cls.__setattr__ = _pov_new_setattr

        return self

    def track_memfun(self, obj:type|object, function:str):
        """
        Track member function calls
        """
        cls = obj if isinstance(obj, type) else type(obj)
        func = cls.__dict__[function]
        self._print("Tracking", f"{cls.__name__}.{function}", "method",
            f"for object {hex(id(obj))}" if not isinstance(obj, type) else "")

        if not hasattr(cls, "_pov_fun_dict"):
            cls._pov_fun_dict = {}
            old_getattribute = cls.__getattribute__
            def _pov_new_getattribute(_self, attr):
                if attr not in cls._pov_fun_dict or \
                        not (isinstance(obj, type) or _self == obj):
                    return old_getattribute(_self, attr)
                def _pov_bind_getattribute(*args, **kwargs):
                    return cls._pov_fun_dict[attr](_self, *args, **kwargs)
                return _pov_bind_getattribute
            cls.__getattribute__ = _pov_new_getattribute
            
        def _pov_new_function(*args, **kwargs):
            depth = 0
            for frame in inspect.stack():
                if frame.function.startswith("_pov"):
                    depth += 1
                else:
                    break
            
            pov = POV(stacklimit=self._stacklimit, file=self._file, _pov_depth=depth)
            pov._print("[f]", f"{cls.__name__}.{function}(")
            for arg in args:
                pov._print("[f]\t", arg, "::", type(arg).__name__)
            for kw in kwargs:
                val = kwargs[kw]
                pov._print("[f]\t", f"{kw}={val}", "::", type(val).__name__)
            
            res = func(*args, **kwargs)
            pov._print("[f]", ")", "=>", res, "::", type(res).__name__)

        cls._pov_fun_dict[function] = _pov_new_function

        return self
    
    def stack(self, stacklimit:int|None):
        """
        Modify the stacklimit
        """
        self._stacklimit = stacklimit
        return self
    
    def print_to(self, file):
        """
        Modify output file
        """
        self._file = file
        return self

def stack(stacklimit, globally=False):
    """
    POV.stack interface
    """
    if globally:
        global _global_stacklimit
        _global_stacklimit = stacklimit
    
    return POV(stacklimit=stacklimit, _pov_depth=1)

def print_to(file, globally=False):
    """
    POV.print_to interface
    """
    if globally:
        global _global_file
        _global_file = file
    return POV(file=file, _pov_depth=1)

def log(*args, **kwargs):
    """
    POV.log interface
    """
    return POV(_pov_depth=1).log(*args, **kwargs)

def view(*exprs):
    """
    POV.view interface
    """
    return POV(_pov_depth=1).view(*exprs)

def interact(normal_exit=False, normal_quit=True):
    """
    POV.interact interface
    """
    return POV(_pov_depth=1).interact(normal_exit=normal_exit, normal_quit=normal_quit)

def track_attr(obj, *attrs, all_attrs=False):
    """
    POV.track_attr interface
    """
    return POV(_pov_depth=1).track_attr(obj, *attrs, all_attrs=all_attrs)

def track_memfun(obj, function):
    """
    POV.track_memfun interface
    """
    return POV(_pov_depth=1).track_memfun(obj, function)