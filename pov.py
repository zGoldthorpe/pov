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
        if not stacklimit:
            stacklimit = len(self._stack)
        
        self._log = []
        self.cons = POV.Console(self)

        for frame in self._stack:
            if frame.filename == __file__:
                continue
            self._log.append((self.cons.path, (f"{self.cons.path(frame.filename)}:{self.cons.info(frame.lineno)} ({self.cons.func(frame.function)})",), {}))
            stacklimit -= 1
            if stacklimit == 0:
                break
        self._log.reverse()
    
    def flush(self):
        """
        Flush output
        """
        if any("[/]" not in str(cons) for cons, _, _ in self._log):
            for cons, args, kwargs in self._log:
                kwargs["file"] = self._file
                print(self.cons.header, cons, *args, **kwargs)
            self._log.clear()

        return self
    
    def __del__(self):
        self.flush()

    def _print(self, cons:str, *args, **kwargs):
        try:
            cons = getattr(self.cons, cons)
        except AttributeError:
            self._print("warn", f"POV does not support \"{self.cons.const(cons)}\" console attribute")
            cons = self.cons.info
        self._log.append((cons, args, kwargs))
        return self

    def _get_context(self):
        frame = self._stack[0].frame
        return dict(frame.f_locals, **frame.f_globals)

    def info(self, *args, **kwargs):
        """
        Simple logger; behaves like an ordinary print.
        """
        return self._print("info", *args, **kwargs).flush()
    
    def ok(self, *args, **kwargs):
        """
        Log an 'ok' event; behaves like an ordinary print.
        """
        return self._print("ok", *args, **kwargs).flush()

    def bad(self, *args, **kwargs):
        """
        Log a 'bad' event; behaves like an ordinary print.
        """
        return self._print("bad", *args, **kwargs).flush()
    
    def warn(self, *args, **kwargs):
        """
        Log a warning; behaves like an ordinary print.
        """
        return self._print("warn", *args, **kwargs).flush()
    
    def view(self, *exprs:str):
        """
        View the value of various expressions.
        """
        context = self._get_context()
        
        for expr in exprs:
            if not isinstance(expr, str):
                self._print("ok", self.cons.const(expr), sep='\t')
                continue
            try:
                val = eval(expr, context)
                self._print("ok", f"\t{self.cons.expr(expr)}",
                            "=>", self.cons.const(val),
                            "::", self.cons.obj(type(val).__name__))
            except Exception as e:
                self._print("bad", f"\t{self.cons.expr(expr)}",
                            "><", self.cons.obj(type(e).__name__),
                            "::", self.cons.bad(e))

        return self.flush()
    
    def check(self, *exprs:str, exit_on_failure=False, interact_on_failure=False):
        """
        Check if expressions evaluate (or cast) to True.
        """
        context = self._get_context()

        all_true = True
        for expr in exprs:
            if not isinstance(expr, str):
                if not expr:
                    all_true = False
                    self._print("warn", self.cons.const(expr))
                else:
                    self._print("ok", self.cons.const(expr))
            else:
                try:
                    val = eval(expr, context)
                    if not val:
                        all_true = False
                        self._print("warn", self.cons.expr(expr), "=>", self.cons.const(val))
                    else:
                        self._print("ok", self.cons.expr(expr), "=>", self.cons.const(val))
                except Exception as e:
                    all_true = False
                    self._print("bad", self.cons.expr(expr), "><", self.cons.obj(type(e).__name__), "::", self.cons.bad(e))
        
        if not all_true:
            self._print("warn", self.cons.bad("Some assertions failed."))
            if interact_on_failure:
                self.interact()
            if exit_on_failure:
                self._print("warn", "Exiting due to failed assertions...")
                exit(1)
        else:
            self._print("ok", self.cons.good("All checks passed."))

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
        attr_msg = ("all attrs",) if all in attrs else map(self.cons.var, attrs)
        self._print("info", "Tracking", *attr_msg,
                    "for", self.cons.obj(cls.__name__),
                    f"object {self.cons.id(hex(id(obj)))}" if not isinstance(obj, type) else "objects"
                    )
        
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
                            "attr",
                            f"{self.cons.obj(cls.__name__)}.{self.cons.var(attr)} := {self.cons.const(value)}",
                            "::", self.cons.obj(type(value).__name__),
                            f"[{self.cons.id(hex(id(self_)))}]"
                        )
                    
                    if isinstance(value, dict):
                        value = POVDict(value)\
                            .stack(self._stacklimit)\
                            .print_to(self._file)\
                            .name(f"{self.cons.obj(cls.__name__)}<{self.cons.id(hex(id(self_)))}>.{self.cons.var(attr)}")
                    elif isinstance(value, list):
                        value = POVList(value)\
                            .stack(self._stacklimit)\
                            .print_to(self._file)\
                            .name(f"{self.cons.obj(cls.__name__)}<{self.cons.id(hex(id(self_)))}>.{self.cons.var(attr)}")
                    
                return old_setattr(self_, attr, value)
            
            cls.__setattr__ = _pov_new_setattr

        attr_dict = cls._pov_attr_dict.setdefault(obj, {})
        pov_params = dict(stacklimit=self._stacklimit, file=self._file)
        for attr in attrs:
            attr_dict[attr] = pov_params

        return self.flush()

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

        funcname = f"{self.cons.obj(cls.__name__)}.{self.cons.func(function)}" \
                if isinstance(obj, type) else \
                f"{self.cons.obj(cls.__name__)}<{self.cons.id(hex(id(obj)))}>.{self.cons.func(function)}"
        cls._pov_fun_dict[function] = self.track(func, name=funcname)

        return self

    def track(self, target=None, *, name=None, attrs=(), interact_on_exception=False, _name=None):
        """
        Decorator wrapping functions and classes to enable tracking
        attrs:  a tuple or list of strings / the builtin `all` indicating which attributes
                to track (cf. track_attr)
        """
        def _pov_wrapper(target_):

            if isinstance(target_, type):
                if _name:
                    target_name = _name
                else:
                    target_name = self.cons.obj(name if name else target_.__name__)
                    
                self._print("info", "Tracking class", target_name).flush()
                target_attrs = attrs if isinstance(attrs, (tuple, list)) else [attrs]
                if target_attrs:
                    self.track_attr(target_, *target_attrs)

                bases = (target_,)
                body = {}
                for member, definition in target_.__dict__.items():
                    if callable(definition) and member not in ["__repr__", "__str__", "__setattr__", "__getattr__"]:
                        body[member] = self.track(definition, _name=f"{target_name}.{self.cons.func(member)}")
                    elif isinstance(definition, property):
                        fget = definition.fget
                        fset = definition.fset
                        fdel = definition.fdel
                        fname = f"{self.cons.obj(target_name)}.{self.cons.func(member)}"
                        if fget:
                            fget = self.track(fget, _name=fname + f"<{self.cons.id('get')}>", interact_on_exception=interact_on_exception)
                        if fset:
                            fset = self.track(fset, _name=fname + f"<{self.cons.id('set')}>", interact_on_exception=interact_on_exception)
                        if fdel:
                            fdel = self.track(fdel, _name=fname + f"<{self.cons.id('del')}>", interact_on_exception=interact_on_exception)
                        body[member] = property(fget, fset, fdel)
                    else:
                        body[member] = definition
                
                return type(name if name else target_.__name__, bases, body)

            else:
                if _name:
                    target_name = _name
                else:
                    target_name = self.cons.func(name if name else target_.__name__)

                self._print("info", "Tracking function", target_name).flush()

                def _pov_tracked_function(*args, **kwargs):
                    pov = POV(
                        stacklimit=self._stacklimit,
                        file=self._file,
                        _pov_depth=1
                    )
                    name = str(target_name)
                    if isinstance(target_, staticmethod):
                        args = args[1:]
                        name += f"<{self.cons.id('static')}>"
                    
                    pov._print("func", f"{name}(")
                    for arg in args:
                        pov._print("func", "\t", self.cons.const(arg),
                                   "::", self.cons.obj(type(arg).__name__))
                    for kw, val in kwargs.items():
                        pov._print("func", "\t", f"{self.cons.var(kw)}={self.cons.const(val)}",
                                   "::", self.cons.obj(type(val).__name__))

                    try:
                        res = target_(*args, **kwargs)
                        pov._print("ok", ")", "=>", self.cons.const(res),
                                   "::", self.cons.obj(type(res).__name__)).flush()
                    except Exception as exc:
                        pov._print("bad", ")", "><", self.cons.obj(type(exc).__name__), "::", self.cons.bad(exc)).flush()
                        if interact_on_exception:
                            pov.interact()
                        raise exc
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

    ### console ANSI formatting class ###
    class Console:

        class Printer:

            def __init__(self, content, style, pov, main):
                self._content = content
                self._style = style
                self._pov = pov
                self._main = main
            
            def _ansi_supported(self) -> bool:
                return sys.platform != 'win32' and hasattr(self._pov._file, "isatty") and self._pov._file.isatty()

            def __repr__(self):
                if self._ansi_supported():
                    return f"\033[{'1;' if self._main else ''}{self._style}m{self._content}\033[m"
                return str(self._content)
            
            def __call__(self, content):
                return POV.Console.Printer(content, self._style, self._pov, False)

        def __init__(self, pov):
            self.header = POV.Console.Printer("POV", "41;37", pov, True)
            for attr, c, style in [
                        ("path", '/', "2"),
                        ("bad",  '-', "31"),
                        ("ok",   '+', "32"),
                        ("warn", '!', "33"),
                        ("func", 'f', "34"),
                        ("attr", 'a', "35"),
                        ("info", 'i', "36"),
                        ("norm", ' ', "37")
                    ]:
                setattr(self, attr, POV.Console.Printer(f"[{c}]", style, pov, True))
            for attr, style in [
                        ("var", "35;3"),
                        ("expr", "35"),
                        ("obj", "36;1"),
                        ("const", "33;3"),
                        ("id", "33;2"),
                    ]:
                setattr(self, attr, POV.Console.Printer(attr, style, pov, False))
        


##### POV data structure tracking #####

class POVObj:
    """
    Base class for wrapping Python data structures
    """
    def __init__(self, name, base_type):
        self._stacklimit = _global_stacklimit
        self._file = _global_file
        self._name = name
        self._base_type = base_type
        self.cons = self._pov.cons
        
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
        return f"{self._name}{self.cons.expr(self._base_type.__repr__(self))}"

class POVDict(POVObj, dict):
    """
    Dictionary wrapper, to track modifications and "get" key-misses
    """

    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        POVObj.__init__(self, "POVDict", dict)
    
    def __delitem__(self, key, /):
        self._pov._print("attr", "del", self._name, '[', self.cons.var(key), "::", self.cons.obj(type(key).__name__), ']').flush()
        return dict.__delitem__(self, key)
    
    def __setitem__(self, key, value, /):
        self._pov._print("attr", self._name, '[', self.cons.var(key), "::", self.cons.obj(type(key).__name__), ']',
                         ":=", self.cons.const(value), "::", self.cons.obj(type(value).__name__)).flush()
        return dict.__setitem__(self, key, value)
    
    def __ior__(self, rhs, /):
        pov = self._pov
        pov._print("attr", self._name, "|=")
        rhs = dict(rhs)
        for k, v in rhs:
            pov._print("attr", "\t", self.cons.var(k), "::", self.cons.obj(type(k).__name__),
                       "=>", self.cons.const(v), "::", self.cons.obj(type(v).__name__))
        pov.flush()
        return dict.__ior__(self, rhs)

    def clear(self, /):
        self._pov._print("attr", self._name, 'cleared')
        return dict.clear(self)
    
    def get(self, key, default=None, /):
        if key not in self:
            self._pov._print("attr", self._name, 'get(', self.cons.var(key), "::", self.cons.obj(type(key).__name__), ') missed',
                             "=>", self.cons.const(default), "::", self.cons.obj(type(default).__name__)).flush()
        return dict.get(self, key, default)
    
    def pop(self, key, default=None, /):
        had = key in self
        value = dict.pop(self, key, default)
        self._pov._print("attr", self._name, "pop(", self.cons.var(key), "::", self.cons.obj(type(key).__name__), ')',
                        self.cons.info("<miss>" if not had else "<hit>"),
                        "=>", self.cons.const(value), "::", self.cons.obj(type(value).__name__)).flush()
        return value
    
    def popitem(self, /):
        k, v = dict.popitem(self)
        self._pov._print("attr", self._name, "popitem", "=>",
                         '(', self.cons.var(k), "::", self.cons.obj(type(k).__name__),
                         ',', self.cons.const(v), "::", self.cons.obj(type(v).__name__), ')').flush()
        return k, v
    
    def setdefault(self, key, default=None, /):
        had = key in self
        value = dict.setdefault(self, key, default)
        self._pov._print("attr", self._name, "setdefault(", self.cons.var(key), "::", self.cons.obj(type(key).__name__), ')',
                         '=>', self.cons.const(value), "::", self.cons.obj(type(value).__name__),
                         self.cons.info("<no update>" if had else "<updated>")).flush()
        return value
    
    def update(self, *args, **kwargs):
        pov = self._pov
        pov._print("attr", self._name, "update:")
        for arg in args:
            arg = dict(arg)
            for key in arg:
                val = arg[key]
                pov._print("attr", "\t", self.cons.var(key), "::", self.cons.obj(type(key).__name__),
                           "=>", self.cons.const(val), "::", self.cons.obj(type(val).__name__))
        for kw in kwargs:
            val = kwargs[kw]
            pov._print("attr", "\t", self.cons.var(kw), "::", self.cons.obj(type(kw).__name__),
                       "=>", self.cons.const(val), "::", self.cons.obj(type(val).__name__))
        pov.flush()
        return dict.update(self, *args, **kwargs)

class POVList(POVObj, list):
    
    def __init__(self, *args, **kwargs):
        list.__init__(self, *args, **kwargs)
        POVObj.__init__(self, "POVList", list)
    
    def __delitem__(self, key, /):
        self._pov._print("attr", "del", self._name, f"[{self.cons.const(key)}]").flush()
        return list.__delitem__(self, key)
    
    def __iadd__(self, rhs, /):
        rhs = list(rhs)
        pov = self._pov
        pov._print("attr", self._name, "+=")
        for it in rhs:
            pov._print("attr", "\t", self.cons.const(it), "::", self.cons.obj(type(it).__name__)).flush()
        return list.__iadd__(self, rhs)
    
    def __imul__(self, mul, /):
        self._pov._print("attr", self._name, "*=", self.cons.const(mul), "::", self.cons.obj(type(mul).__name__)).flush()
        return list.__imul__(self, mul)
    
    def __setitem__(self, index, value, /):
        self._pov._print("attr", self._name,
                        f"[{self.cons.const(index)}]",
                        ":=", self.cons.const(value), "::", self.cons.obj(type(value).__name__)).flush()
        return list.__setitem__(self, index, value)
    
    def append(self, obj, /):
        self._pov._print("attr", self._name, "append(", self.cons.const(obj), "::", self.cons.obj(type(obj).__name__), ")").flush()
        return list.append(self, obj)

    def clear(self, /):
        self._pov._print("attr", self._name, "cleared").flush()
        return list.clear(self)
    
    def insert(self, index, obj, /):
        self._pov._print("attr", self._name, "insert", self.cons.const(obj), "::", self.cons.obj(type(obj).__name__),
                         "at index", self.cons.const(index)).flush()
        return list.insert(self, index, obj)
    
    def pop(self, index=-1, /):
        value = list.pop(self, index)
        self._pov._print("attr", self._name, f"pop({self.cons.const(index)})",
                         "=>", self.cons.const(value), "::", self.cons.obj(type(value).__name__)).flush()
        return value
    
    def remove(self, obj, /):
        self._pov._print("attr", self._name, "removing", self.cons.const(obj), "::", self.cons.obj(type(obj).__name__)).flush()
        return list.remove(self, obj)

    def reverse(self, /):
        self._pov._print("attr", self._name, "in-place reversal").flush()
        return list.reverse(self)
    
    def sort(self, *, key=None, reverse=False):
        self._pov._print("attr", self._name, "sorted").flush()
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

def info(*args, value=0, **kwargs):
    """
    POV.info interface
    """
    return POV(_pov_depth=1).info(*args, value=value, **kwargs)

def ok(*args, value=0, **kwargs):
    """
    POV.ok interface
    """
    return POV(_pov_depth=1).ok(*args, value=value, **kwargs)

def bad(*args, value=0, **kwargs):
    """
    POV.bad interface
    """
    return POV(_pov_depth=1).bad(*args, value=value, **kwargs)

def warn(*args, value=0, **kwargs):
    """
    POV.warn interface
    """
    return POV(_pov_depth=1).warn(*args, value=value, **kwargs)

def view(*exprs):
    """
    POV.view interface
    """
    return POV(_pov_depth=1).view(*exprs)

def check(*exprs, exit_on_failure=False, interact_on_failure=False):
    """
    POV.check interface
    """
    return POV(_pov_depth=1).check(*exprs, exit_on_failure=exit_on_failure, interact_on_failure=interact_on_failure)

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

def _pov_excepthook(exctype, value, tb):
    pov = POV()
    pov._log = []
    pov.bad(pov.cons.header("Program terminated with uncaught exception:"))
    while tb:
        frame = tb.tb_frame
        co = frame.f_code
        func = co.co_name
        file = co.co_filename
        line = tb.tb_lineno

        if file != __file__:

            try:
                with open(file) as src_file:
                    src = src_file.readlines()[line-1].strip()
            except OSError:
                src = None
            
            pov.bad(f"{pov.cons.path(co.co_filename)}:{pov.cons.info(line)} ({pov.cons.func(func)})")
            if src:
                pov.bad(f"\t{pov.cons.expr(src)}")

        tb = tb.tb_next
    
    pov.bad(pov.cons.obj(exctype.__name__), "::", pov.cons.bad(value))
    exit(-1)

sys.__excepthook__ = _pov_excepthook
sys.excepthook = _pov_excepthook