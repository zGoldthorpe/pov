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

    class LOG:
        class log_type:
            def __init__(self, symbol, style):
                self.symbol = symbol
                self.style = style

            def show(self, pretty):
                if pretty and sys.platform != 'win32':
                    return f"{self.style}{self.symbol}\033[m"
                return self.symbol
        
        INFO = log_type("[i]", "\033[33m")
        FUNC = log_type("[f]", "\033[34m")
        ATTR = log_type("[a]", "\033[35m")
        PATH = log_type("[/]", "\033[2m")
        EXCP = log_type("[-]", "\033[31m")
        GOOD = log_type("[+]", "\033[32m")
            

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
        if not stacklimit:
            stacklimit = len(self._stack)
        
        self._log = []

        for frame in self._stack:
            if frame.function.startswith("_pov"):
                continue
            self._log.append((POV.LOG.PATH, (f"{frame.filename}:{frame.lineno} ({frame.function})",), {}))
            stacklimit -= 1
            if stacklimit == 0:
                break
        self._log.reverse()
    
    def flush(self):
        """
        Flush output
        """
        isatty = hasattr(self._file, 'isatty') and self._file.isatty()
        if self._log:
            for log, args, kwargs in self._log:
                kwargs["file"] = self._file
                print(log.show(isatty), *args, **kwargs)
            self._log.clear()

        return self
    
    def __del__(self):
        self.flush()

    def _print(self, log:LOG, *args, **kwargs):
        self._log.append((log, args, kwargs))
        return self

    def _get_context(self):
        frame = self._stack[0].frame
        return dict(frame.f_locals, **frame.f_globals)

    def log(self, *args, value=0, **kwargs):
        """
        Simple logger; behaves like an ordinary print.
        """
        log = POV.LOG.GOOD if value > 0 else POV.LOG.EXCP if value < 0 else POV.LOG.INFO
        self._print(log, *args, **kwargs)
        return self
    
    def view(self, *exprs : str):
        """
        View the value of various expressions.
        """

        context = self._get_context()
        
        for expr in exprs:
            if not isinstance(expr, str):
                self._print(POV.LOG.GOOD, expr, sep='\t')
                continue
            try:
                val = eval(expr, context)
                self._print(POV.LOG.GOOD, f"\t{expr}", "=>", val, "::", type(val).__name__)
            except Exception as e:
                self._print(POV.LOG.EXCP, f"\t{expr}", "><", type(e).__name__, "::", e)

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
        
        code.interact(banner=f"[ ] Entering interactive mode.\n{msg}", local=context, exitmsg="[ ] Resuming normal execution...")

        return self

    def track_attr(self, obj:type|object, *attrs:str):
        """
        Track all modifications of a class or object's attrs.
        Use `all` (the built-in function) to track all attributes;
        otherwise, attributes should be strings.
        """
        cls = obj if isinstance(obj, type) else type(obj)
        old_setattr = cls.__setattr__
        self._print(POV.LOG.INFO, "Tracking", "all attrs" if all in attrs else ", ".join(attrs),
                    "for", cls.__name__, f"object {hex(id(obj))}" if not isinstance(obj, type) else "objects"
                    ).flush()
        
        if not hasattr(cls, "_pov_attr_dict"):
            cls._pov_attr_dict = {cls : {}}
            """
            _pov_attr_dict[cls]: attributes tracked for all instances of cls
            _pov_attr_dict[obj]: attributes tracked for just obj
            The value is another dict, which maps str|all to POV params
            """
            old_setattr  = cls.__setattr__

            def _pov_new_setattr(self_, attr, value):

                pov_params = {}
                pov_params.update(cls._pov_attr_dict[cls].get(all, {}))
                cls_attr_dict = cls._pov_attr_dict.get(obj, {})
                pov_params.update(cls_attr_dict.get(all, {}))
                pov_params.update(cls_attr_dict.get(attr, {}))
                
                if pov_params:

                    POV(_pov_depth=1, **pov_params)._print(
                            POV.LOG.ATTR,
                            f"{cls.__name__}.{attr} := {value}",
                            "::", type(value).__name__,
                            f"[{hex(id(self_))}]"
                        )
                    
                    if isinstance(value, dict):
                        value = POVDict(value)\
                            .stack(self._stacklimit)\
                            .print_to(self._file)\
                            .name(f"{cls.__name__}<{hex(id(self_))}>.{attr}")
                    elif isinstance(value, list):
                        value = POVList(value)\
                            .stack(self._stacklimit)\
                            .print_to(self._file)\
                            .name(f"{cls.__name__}<{hex(id(self_))}>.{attr}")
                    
                return old_setattr(self_, attr, value)
            
            cls.__setattr__ = _pov_new_setattr

        attr_dict = cls._pov_attr_dict.setdefault(obj, {})
        pov_params = dict(stacklimit=self._stacklimit, file=self._file)
        for attr in attrs:
            attr_dict[attr] = pov_params

        return self

    def track_memfun(self, obj:type|object, function:str):
        """
        Track member function calls
        """
        cls = obj if isinstance(obj, type) else type(obj)
        func = cls.__dict__[function]

        if not hasattr(cls, "_pov_fun_dict"):
            cls._pov_fun_dict = {}
            old_getattribute = cls.__getattribute__
            def _pov_new_getattribute(self_, attr):
                if attr not in cls._pov_fun_dict or \
                        not (isinstance(obj, type) or self_ == obj):
                    return old_getattribute(self_, attr)
                def _pov_bind_getattribute(*args, **kwargs):
                    return cls._pov_fun_dict[attr](self_, *args, **kwargs)
                return _pov_bind_getattribute
            cls.__getattribute__ = _pov_new_getattribute

        funcname = f"{cls.__name__}.{function}" if isinstance(obj, type) else f"{cls.__name__}<{hex(id(obj))}>.{function}"
        cls._pov_fun_dict[function] = self.track(func, name=funcname)

        return self

    def track(self, target=None, *, name=None, attrs=()):
        """
        Decorator wrapping functions and classes to enable tracking
        attrs:  a tuple or list of strings / the builtin `all` indicating which attributes
                to track (cf. track_attr)
        """
        def _pov_wrapper(target_):
            target_name = name if name else target_.__name__

            if isinstance(target_, type):
                self._print(POV.LOG.INFO, "Tracking class", target_name).flush()
                target_attrs = attrs if isinstance(attrs, (tuple, list)) else [attrs]
                if target_attrs:
                    self.track_attr(target_, *target_attrs)

                bases = (target_,)
                body = {}
                for member, definition in target_.__dict__.items():
                    if callable(definition) and member not in ["__repr__", "__str__", "__setattr__", "__getattr__"]:
                        body[member] = self.track(definition, name=f"{target_name}.{member}")
                    elif isinstance(definition, property):
                        fget = definition.fget
                        fset = definition.fset
                        fdel = definition.fdel
                        if fget:
                            fget = self.track(fget, name=f"{target_name}.{member}<get>")
                        if fset:
                            fset = self.track(fset, name=f"{target_name}.{member}<set>")
                        if fdel:
                            fdel = self.track(fdel, name=f"{target_name}.{member}<del>")
                        body[member] = property(fget, fset, fdel)
                    else:
                        body[member] = definition
                
                return type(target_name, bases, body)

            else:
                self._print(POV.LOG.INFO, "Tracking function", target_name).flush()

                def _pov_tracked_function(*args, **kwargs):
                    pov = POV(
                        stacklimit=self._stacklimit,
                        file=self._file,
                        _pov_depth=1
                    )
                    name = target_name
                    if isinstance(target_, staticmethod):
                        args = args[1:]
                        name += "<static>"
                    
                    pov._print(POV.LOG.FUNC, f"{name}(")
                    for arg in args:
                        pov._print(POV.LOG.FUNC, "\t", arg, "::", type(arg).__name__)
                    for kw, val in kwargs.items():
                        pov._print(POV.LOG.FUNC, "\t", f"{kw}={val}", "::", type(val).__name__)

                    res = target_(*args, **kwargs)
                    pov._print(POV.LOG.FUNC, ")", "=>", res, "::", type(res).__name__)
                    
                    return res
                return _pov_tracked_function
            
        return _pov_wrapper if target is None else _pov_wrapper(target)
    
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

class POVObj:
    """
    Base class for wrapping Python data structures
    """
    def __init__(self, name, base_type):
        self._stacklimit = _global_stacklimit
        self._file = _global_file
        self._name = name
        self._base_type = base_type
        
    def stack(self, stacklimit):
        self._stacklimit = stacklimit
        return self
    
    def print_to(self, file):
        self._file = file
        return self
    
    def name(self, name):
        self._name = name
        return self
    
    @property
    def _pov(self):
        return POV(stacklimit=self._stacklimit, file=self._file, _pov_depth=2)
    
    def __repr__(self):
        return f"{self._name}{self._base_type.__repr__(self)}"

class POVDict(POVObj, dict):
    """
    Dictionary wrapper, to track modifications and "get" key-misses
    """

    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        POVObj.__init__(self, "POVDict", dict)
    
    def __delitem__(self, key, /):
        self._pov._print(POV.LOG.ATTR, "del", self._name, '[', key, "::", type(key).__name__, ']')
        return dict.__delitem__(self, key)
    
    def __setitem__(self, key, value, /):
        self._pov._print(POV.LOG.ATTR, self._name, '[', key, "::", type(key).__name__, ']',
                         ":=", value, "::", type(value).__name__)
        return dict.__setitem__(self, key, value)
    
    def __ior__(self, rhs, /):
        pov = self._pov
        pov._print(POV.LOG.ATTR, self._name, "|=")
        rhs = dict(rhs)
        for k, v in rhs:
            pov._print(POV.LOG.ATTR, "\t", k, "::", type(k).__name__, "=>", v, "::", type(v).__name__)
        return dict.__ior__(self, rhs)

    def clear(self, /):
        self._pov._print(POV.LOG.ATTR, self._name, 'cleared')
        return dict.clear(self)
    
    def get(self, key, default=None, /):
        if key not in self:
            self._pov._print(POV.LOG.ATTR, self._name, 'get(', key, "::", type(key).__name__, ') missed',
                             "=>", default, "::", type(default).__name__)
        return dict.get(self, key, default)
    
    def pop(self, key, default=None, /):
        had = key in self
        value = dict.pop(self, key, default)
        self._pov._print(POV.LOG.ATTR, self._name, "pop(", key, "::", type(key).__name__, ')',
                        "<miss>" if not had else "<hit>", "=>", value, "::", type(value).__name__)
        return value
    
    def popitem(self, /):
        k, v = dict.popitem(self)
        self._pov._print(POV.LOG.ATTR, self._name, "popitem", "=>",
                         '(', k, "::", type(k).__name__,
                         ',', v, "::", type(v).__name__, ')')
        return k, v
    
    def setdefault(self, key, default=None, /):
        had = key in self
        value = dict.setdefault(self, key, default)
        self._pov._print(POV.LOG.ATTR, self._name, "setdefault(", key, "::", type(key).__name__, ')',
                         '=>', value, "::", type(value).__name__, "<no update>" if had else "<updated>")
        return value
    
    def update(self, *args, **kwargs):
        pov = self._pov
        pov._print(POV.LOG.ATTR, self._name, "update:")
        for arg in args:
            arg = dict(arg)
            for key in arg:
                val = arg[key]
                pov._print(POV.LOG.ATTR, "\t", key, "::", type(key).__name__, "=>", val, "::", type(val).__name__)
        for kw in kwargs:
            val = kwargs[kw]
            pov._print(POV.LOG.ATTR, "\t", kw, "::", type(kw).__name__, "=>", val, "::", type(val).__name__)
        return dict.update(self, *args, **kwargs)

class POVList(POVObj, list):
    
    def __init__(self, *args, **kwargs):
        list.__init__(self, *args, **kwargs)
        POVObj.__init__(self, "POVList", list)
    
    def __delitem__(self, key, /):
        self._pov._print(POV.LOG.ATTR, "del", self._name, '[', key, "::", type(key).__name__, ']')
        return list.__delitem__(self, key)
    
    def __iadd__(self, rhs, /):
        rhs = list(rhs)
        pov = self._pov
        pov._print(POV.LOG.ATTR, self._name, "+=")
        for it in rhs:
            pov._print(POV.LOG.ATTR, "\t", it, "::", type(it).__name__)
        return list.__iadd__(self, rhs)
    
    def __imul__(self, mul, /):
        self._pov._print(POV.LOG.ATTR, self._name, "*=", mul, "::", type(mul).__name__)
        return list.__imul__(self, mul)
    
    def __setitem__(self, index, value, /):
        self._pov._print(POV.LOG.ATTR, self._name,
                        f"[{index}]",
                        ":=", value, "::", type(value).__name__)
        return list.__setitem__(self, index, value)
    
    def append(self, obj, /):
        self._pov._print(POV.LOG.ATTR, self._name, "append(", obj, "::", type(obj).__name__, ")")
        return list.append(self, obj)

    def clear(self, /):
        self._pov._print(POV.LOG.ATTR, self._name, "cleared")
        return list.clear(self)
    
    def insert(self, index, obj, /):
        self._pov._print(POV.LOG.ATTR, self._name, "insert", obj, "::", type(obj).__name__, "at index", index)
        return list.insert(self, index, obj)
    
    def pop(self, index=-1, /):
        value = list.pop(self, index)
        self._pov._print(POV.LOG.ATTR, self._name, f"pop({index})", "=>", value, "::", type(value).__name__)
        return value
    
    def remove(self, obj, /):
        self._pov._print(POV.LOG.ATTR, self._name, "removing", obj, "::", type(obj).__name__)
        return list.remove(self, obj)

    def reverse(self, /):
        self._pov._print(POV.LOG.ATTR, self._name, "in-place reversal")
        return list.reverse(self)
    
    def sort(self, *, key=None, reverse=False):
        self._pov._print(POV.LOG.ATTR, self._name, "sorted")
        return list.sort(self, key=key, reverse=reverse)

##### Front-end API #####

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

def log(*args, value=0, **kwargs):
    """
    POV.log interface
    """
    return POV(_pov_depth=1).log(*args, value=value, **kwargs)

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

def track_attr(obj, *attrs):
    """
    POV.track_attr interface
    """
    return POV(_pov_depth=1).track_attr(obj, *attrs)

def track_memfun(obj, function):
    """
    POV.track_memfun interface
    """
    return POV(_pov_depth=1).track_memfun(obj, function)

def track(target=None, *, name=None, attrs=()):
    """
    POV.track interface
    """
    return POV(_pov_depth=1).track(target, name=name, attrs=attrs)