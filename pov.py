"""
POV module

Glorified printing functionality
"""

import code
import inspect
import sys

class POV:

    def __init__(self, *, stacklimit=1, file=sys.stderr, _pov_depth=0):
        """
        Initialisation parameters:
        stacklimit: how many levels of stack context to print (None for no limit)
                    (default: 1)
        file:       print output file
                    (default: stderr)
        """
        self._stack = inspect.stack()[_pov_depth+1:]
        self._stacklimit = stacklimit
        self._file = file
        stackrange = range(stacklimit if stacklimit else len(self._stack))
        self._log = []
        for frame, _ in reversed(list(zip(self._stack, stackrange))):
            self._print("[/]", f"{frame.filename}:{frame.lineno} ({frame.function})")
    
    def __del__(self):
        for args, kwargs in self._log:
            kwargs["file"] = self._file
            print(*args, **kwargs)

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

    def track_attr(self, obj:type|object, *members:str, all_members=False):
        """
        Track all modifications of a class or object's members.
        """
        cls = obj if isinstance(obj, type) else type(obj)
        old_setattr = cls.__setattr__

        def _pov_new_setattr(_self, _attr, _value):
            depth = 0
            for frame in inspect.stack():
                if frame.function == "_pov_new_setattr":
                    depth += 1
                else:
                    break

            if (all_members or _attr in members) and (isinstance(obj, type) or _self == obj):
                POV(stacklimit=self._stacklimit,
                    file=self._file,
                    _pov_depth=depth)._print(f"[t]\t{obj}.{_attr}", ":=", _value)
            return old_setattr(_self, _attr, _value)
        
        cls.__setattr__ = _pov_new_setattr

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
    return POV(_pov_depth=1).interact(normal_exit=normal_exit, normal_quit=normal_quit)

