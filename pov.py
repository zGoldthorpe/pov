"""
POV module

Glorified printing functionality
"""

import code
import inspect
import os
import sys

_global_file=sys.stderr

class POV:

    def __init__(self):
        self._stack = inspect.stack()

        self._context = {}

        for finfo in self._stack:
            frame = finfo.frame
            if finfo.filename == __file__:
                continue

            self._context = dict(frame.f_locals, **frame.f_globals)
            break

    @staticmethod
    def print_to(self, file):
        """
        Change output destination (defaults to sys.stderr)
        """
        global _global_file
        _global_file = file
        return self

    def info(self, *args, **kwargs):
        """
        Simple logger; behaves like an ordinary print.
        """
        with POVPrint.info() as printer:
            printer.print(*args, **kwargs)
        return self
    
    def ok(self, *args, **kwargs):
        """
        Log an 'ok' event; behaves like an ordinary print.
        """
        with POVPrint.ok() as printer:
            printer.print(*args, **kwargs)
        return self

    def bad(self, *args, **kwargs):
        """
        Log a 'bad' event; behaves like an ordinary print.
        """
        with POVPrint.bad() as printer:
            printer.print(*args, **kwargs)
        return self
    
    def warn(self, *args, **kwargs):
        """
        Log a warning; behaves like an ordinary print.
        """
        with POVPrint.warn() as printer:
            printer.print(*args, **kwargs)
        return self
    
    def view(self, *exprs:str):
        """
        View the value of various expressions.
        """
        
        with POVPrint.ok() as printer:
            printer.print("Expression view:")
            for expr in exprs:
                if not isinstance(expr, str):
                    printer.append(POVPrint.ok(), POVPrint.value(expr))
                    continue
                try:
                    val = eval(expr, self._context)
                    printer.append(POVPrint.ok(), POVPrint.expr(expr), "=>", POVPrint.value(val))
                except Exception as exc:
                    printer.append(POVPrint.bad(), POVPrint.expr(expr), "><", POVPrint.exception(exc))

        return self
    
    def check(self, *exprs:str, exit_on_failure=False, interact_on_failure=False):
        """
        Check if expressions evaluate (or cast) to True.
        """

        all_true = True
        with POVPrint.info() as printer:
            printer.print("Assertions:")

            for expr in exprs:
                if not isinstance(expr, str):
                    if not expr:
                        all_true = False
                        printer.append(POVPrint.warn(), POVPrint.value(expr))
                    else:
                        printer.append(POVPrint.ok(), POVPrint.value(expr))
                else:
                    try:
                        val = eval(expr, self._context)
                        if not val:
                            all_true = False
                            printer.append(POVPrint.warn(), POVPrint.expr(expr),
                                    "=>", POVPrint.value(val))
                        else:
                            printer.append(POVPrint.ok(), POVPrint.expr(expr),
                                    "=>", POVPrint.value(val))
                    except Exception as exc:
                        all_true = False
                        printer.append(POVPrint.bad(), POVPrint.expr(expr),
                                "><", POVPrint.exception(exc))
        
            if not all_true:
                printer.append(POVPrint.warn(), POVPrint.bad("Some assertions failed."))
                if interact_on_failure:
                    self.interact()
                if exit_on_failure:
                    printer.append(POVPrint.bad(), "Exiting due to failed assertions...")
                    exit(1)
            else:
                printer.append(POVPrint.ok(), POVPrint.ok("All checks passed."))

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
        attr_msg = ("all attrs",) if all in attrs else POVPrint.join(", ", *attrs, cons=POVPrint.var)

        with POVPrint.info() as printer:
            printer.print("Tracking", attr_msg, "for",
                    POVPrint.type(cls) if not isinstance(obj, type) else POVPrint.instance(obj))
        
        if not hasattr(cls, "_pov_attr_dict"):
            cls._pov_attr_dict = {cls : set()}
            """
            _pov_attr_dict[cls]: attributes tracked for all instances of cls
            _pov_attr_dict[obj]: attributes tracked for just obj
            The value, either way, is a set of attributes (str) or the built-in `all`
            """
            old_setattr  = cls.__setattr__

            def _pov_new_setattr(self_, attr, value):

                if any((
                        all in cls._pov_attr_dict[cls],
                        attr in cls._pov_attr_dict[cls],
                        all in cls._pov_attr_dict.get(obj, {}),
                        attr in cls._pov_attr_dict.get(obj, {}))):
                    
                    with POVPrint.attr() as printer:
                        printer.print(POVPrint.member(obj, attr),
                                ":=", POVPrint.value(value))
                    
                    if isinstance(value, dict):
                        value = POVDict(value, pov_name=POVPrint.member(obj, attr))
                    elif isinstance(value, list):
                        value = POVList(value, pov_name=POVPrint.member(obj, attr))
                    
                return old_setattr(self_, attr, value)
            
            cls.__setattr__ = _pov_new_setattr

        attr_set = cls._pov_attr_dict.setdefault(obj, set())
        for attr in attrs:
            attr_set.add(attr)

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

        funcname = POVPrint.join('.',
                POVPrint.type(obj) if isinstance(obj, type) else POVPrint.instance(obj),
                POVPrint.func(function))
        cls._pov_fun_dict[function] = self.track(func, name=funcname)

        return self

    def track(self, target=None, *, name=None, attrs=(), interact_on_exception=False):
        """
        Decorator wrapping functions and classes to enable tracking
        attrs:  a tuple or list of strings / the builtin `all` indicating which attributes
                to track (cf. track_attr)
        """
        def _pov_wrapper(target_):

            if isinstance(target_, type):
                if name is None:
                    target_name = POVPrint.obj(target_.__name__)
                else:
                    target_name = POVPrint.obj(name) if isinstance(name, str) else name
                
                with POVPrint.info() as printer:
                    printer.print("Tracking class", target_name)

                target_attrs = attrs if isinstance(attrs, (tuple, list)) else [attrs]
                if target_attrs:
                    self.track_attr(target_, *target_attrs)

                bases = (target_,)
                body = {}
                for member, definition in target_.__dict__.items():
                    if callable(definition) and member not in ["__repr__", "__str__", "__setattr__", "__getattr__"]:
                        body[member] = self.track(definition, name=POVPrint.join('.', target_name, POVPrint.func(member)),
                                interact_on_exception=interact_on_exception)
                    elif isinstance(definition, property):
                        fget = definition.fget
                        fset = definition.fset
                        fdel = definition.fdel
                        fname = POVPrint.join('.', target_name, POVPrint.func(member))
                        if fget:
                            fget = self.track(fget, name=POVPrint.template(fname, 'get'),
                                interact_on_exception=interact_on_exception)
                        if fset:
                            fset = self.track(fset, name=POVPrint.template(fname, 'set'),
                                interact_on_exception=interact_on_exception)
                        if fdel:
                            fdel = self.track(fdel, name=POVPrint.template(fname, 'del'),
                                interact_on_exception=interact_on_exception)
                        body[member] = property(fget, fset, fdel)
                    else:
                        body[member] = definition
                
                plain_name = target_.__name__ if name is None else name if isinstance(name, str) else name.plain
                return type(plain_name, bases, body)

            else:

                if name is None:
                    target_name = POVPrint.func(target_.__name__)
                else:
                    target_name = POVPrint.func(name) if isinstance(name, str) else name
                
                with POVPrint.info() as printer:
                    printer.print("Tracking function", target_name)

                def _pov_tracked_function(*args, **kwargs):

                    name = target_name
                    if isinstance(target_, staticmethod):
                        args = args[1:]
                        name = POVPrint.template(name, 'static')
                    
                    with POVPrint.func() as printer:
                        printer.print(POVPrint.join('', name, '('))
                        for arg in args:
                            printer.print('\t', POVPrint.value(arg))
                        for kw, val in kwargs.items():
                            printer.print('\t', POVPrint.join('=',
                                POVPrint.var(kw), POVPrint.value(val)))

                        try:
                            res = target_(*args, **kwargs)
                            printer.append(POVPrint.ok(), ")", "=>", POVPrint.value(res))
                        except Exception as exc:
                            printer.append(POVPrint.bad(), ")", "><", POVPrint.exception(exc))
                            if interact_on_exception:
                                self.interact()
                            raise exc
                    return res
                return _pov_tracked_function
            
        return _pov_wrapper if target is None else _pov_wrapper(target)

    ### console ANSI formatting class ###
    class Printer:

        _parent = None
        _previous_stack = []

        def __init__(self, content, style):
            self._content = content
            self._style = style
            self._main = False
            self._lines = []
        
        def _ansi_supported(self) -> bool:
            global _global_file
            if not hasattr(_global_file, "isatty"):
                return False
            if not _global_file.isatty():
                return False
            if sys.platform == 'win32':
                return "ANSICON" in os.environ
            return True

        def __repr__(self):
            if self._ansi_supported():
                return f"\033[{'1;' if self._main else ''}{self._style}m{self._content}\033[m"
            return str(self._content)

        @property
        def plain(self):
            if hasattr(self._content, "plain"):
                return self._content.plain
            return str(self._content)
        
        def __call__(self, content):
            return POV.Printer(content, self._style)

        def print(self, *args, **kwargs):
            self.append(self, *args, **kwargs)

        def append(self, printer, *args, **kwargs):
            self._lines.append((printer, args, kwargs))

        def __enter__(self):
            self._parent = POV.Printer._parent
            POV.Printer._parent = self
            if self._parent is None:
                self._bars = []
            else:
                self._bars = list(self._parent._bars)
            
            self._bars.append(POV.Printer('|', self._style))

            self._lines = []
            self._child_lines = []
            
            self._stack = []
            for frame in inspect.stack():
                if frame.filename == __file__ or not os.path.exists(frame.filename):
                    continue
                self._stack.append(frame)

            return self
        
        def __exit__(self, exc_type, value, tb):
            global _global_file
            # NB: do NOT revert POV.Printer._previous_stack
            
            stacked_lines = [(list(reversed(self._stack)), self._bars, self._lines)] + self._child_lines

            if self._parent is not None:
                self._parent._child_lines.extend(stacked_lines)
            else:
                def dump(printer, bars, *args, **kwargs):
                    kwargs["file"] = _global_file
                    kwargs["end"] = '\n'
                    print(POVPrint.head(), printer, bars, *args, **kwargs)
                
                for stack, bars, lines in stacked_lines:
                    bars = "".join(map(repr, bars))
                    if len(lines) == 0:
                        continue
                    i = 0
                    while i < min(len(stack), len(POV.Printer._previous_stack)):
                        if stack[i] != POV.Printer._previous_stack[i]:
                            break
                        i += 1
                    if i > 0:
                        if i < len(POV.Printer._previous_stack):
                            dump(POVPrint.path(), bars, POVPrint.frame(stack[i-1]),
                                 POVPrint.path(f"<up {len(POV.Printer._previous_stack)-i}>"))
                    else:
                        dump(POVPrint.path(), bars, POVPrint.path("<new stack>"))

                    for j in range(i, len(stack)):
                        dump(POVPrint.path(), bars, POVPrint.frame(stack[j]))
                    
                    for printer, args, kwargs in lines:
                        dump(printer, bars, *args, **kwargs)

                    POV.Printer._previous_stack = stack

            POV.Printer._parent = self._parent
            

class POVPrint:
    """
    Designated printing styles
    """
    
    def __init__(self, fmt:str, *args, **kwargs):
        self._fmt = fmt
        self._args = args
        self._kwargs = kwargs

    def __repr__(self):
        return self._fmt.format(*self._args, **self._kwargs)
    
    @property
    def plain(self):
        def make_plain(key):
            if hasattr(key, "plain"):
                return key.plain
            return repr(key)
        args = map(make_plain, self._args)
        kwargs = { k : make_plain(v) for k, v in self._kwargs.items() }
        return self._fmt.format(*args, **kwargs)

    ### Style printers ###

    @staticmethod
    def head(arg=None):
        printer = POV.Printer("POV", "41;37")
        return printer if arg is None else printer(arg)

    @staticmethod
    def path(arg=None):
        printer = POV.Printer("[/]", "2")
        return printer if arg is None else printer(arg)

    @staticmethod
    def bad(arg=None):
        printer = POV.Printer("[-]", "31")
        return printer if arg is None else printer(arg)

    @staticmethod
    def ok(arg=None):
        printer = POV.Printer("[+]", "32")
        return printer if arg is None else printer(arg)

    @staticmethod
    def warn(arg=None):
        printer = POV.Printer("[!]", "33")
        return printer if arg is None else printer(arg)

    @staticmethod
    def func(arg=None):
        printer = POV.Printer("[f]", "34")
        return printer if arg is None else printer(arg)

    @staticmethod
    def attr(arg=None):
        printer = POV.Printer("[a]", "35")
        return printer if arg is None else printer(arg)

    @staticmethod
    def info(arg=None):
        printer = POV.Printer("[i]", "36")
        return printer if arg is None else printer(arg)

    @staticmethod
    def norm(arg=None):
        printer = POV.Printer("[ ]", "37")
        return printer if arg is None else printer(arg)

    @staticmethod
    def var(arg=None):
        printer = POV.Printer('', "35;3")
        return printer if arg is None else printer(arg)

    @staticmethod
    def expr(arg=None):
        printer = POV.Printer('', "35")
        return printer if arg is None else printer(arg)

    @staticmethod
    def obj(arg=None):
        printer = POV.Printer('', "36;1")
        return printer if arg is None else printer(arg)

    @staticmethod
    def const(arg=None):
        printer = POV.Printer('', "33;3")
        return printer if arg is None else printer(arg)

    @staticmethod
    def id(arg=None):
        printer = POV.Printer('', "33;2")
        return printer if arg is None else printer(arg)

    ### Styled maccros ###

    @classmethod
    def value(cls, v):
        if isinstance(v, str):
            v = repr(v)
        return cls("{0} :: {1}",
                POVPrint.const(v),
                POVPrint.type(type(v)))

    @classmethod
    def join(cls, jstr, *elts, cons=lambda x:x):
        if len(elts) == 0:
            return ""
        head, *rest = elts
        if len(rest) == 0:
            return cons(head)
        return cls(f"{{0}}{jstr}{{1}}", cons(head), POVPrint.join(jstr, *rest, cons=cons))

    @classmethod
    def type(cls, t):
        module = POVPrint.join('.',
                *filter(lambda m: m != "__main__", t.__module__.split('.')),
                cons=POVPrint.path)
        qualname = POVPrint.join('.',
                *t.__qualname__.split('.'),
                cons=POVPrint.obj)
        if module:
            return cls("{0}.{1}", module, qualname)
        return qualname

    @classmethod
    def function(cls, func):
        module = POVPrint.join('.',
                *filter(lambda m: m != "__main__", func.__module__.split('.')),
                cons=POVPrint.path)
        *os, f = func.__qualname__.split('.')
        f = POVPrint.func(f)
        if os:
            obj = POVPrint.join('.', *os, cons=POVPrint.obj)
        if module:
            if os:
                return cls("{0}.{1}.{2}", module, obj, f)
            return cls("{0}.{1}", module, f)
        if os:
            return cls("{0}.{1}", obj, f)
        return f

    @classmethod
    def exception(cls, exc):
        return cls("{0}: {1}", POVPrint.type(type(exc)), POVPrint.bad(exc))

    @classmethod
    def template(cls, x, *ts):
        return cls("{0}<{1}>", x, POVPrint.join(',', *ts, cons=POVPrint.id))

    @classmethod
    def instance(cls, obj):
        return POVPrint.template(POVPrint.type(type(obj)), POVPrint.id(hex(id(obj))))

    @classmethod
    def member(cls, obj, attr):
        return cls("{0}.{1}",
                POVPrint.type(obj) if isinstance(obj, type) else POVPrint.instance(obj),
                POVPrint.var(attr))

    @classmethod
    def frame(cls, frame):
        filename = frame.filename
        if os.path.exists(filename):
            filename = min(filename, os.path.relpath(filename), key=len)
            with open(filename) as file:
                src = ' '.join(file.readlines()[frame.lineno-1].split())
                if len(src) > 63:
                    src = POVPrint("{0}...{1}", POVPrint.expr(src[:30]), POVPrint.expr(src[-30:]))
                else:
                    src = POVPrint.expr(src)
            return cls("{0}:{1} ({2}) {3}", POVPrint.path(filename), POVPrint.info(frame.lineno),
                            POVPrint.func(frame.function), src)
            
        return cls("{0}:{1} ({2})", POVPrint.path(frame.filename), POVPrint.info(frame.lineno),
                                        POVPrint.func(frame.function))



##### POV data structure tracking #####

class POVObj:
    """
    Base class for wrapping Python data structures
    """
    def __init__(self, name, base_type):
        self._file = _global_file
        self._name = name
        self._base_type = base_type

        with POVPrint.info() as printer:
            printer.print("Intercepting", POVPrint.type(base_type), "instance", name)
    
    def __repr__(self):
        return f"{self._name}{POVPrint.expr(self._base_type.__repr__(self))}"

class POVDict(POVObj, dict):
    """
    Dictionary wrapper, to track modifications and "get" key-misses
    """

    def __init__(self, *args, pov_name="POVDict", **kwargs):
        dict.__init__(self, *args, **kwargs)
        POVObj.__init__(self, pov_name, dict)
    
    def __delitem__(self, key, /):
        with POVPrint.attr() as printer:
            printer.print("del", self._name, '[', self.cons.var(key), "::", self.cons.obj(type(key).__name__), ']')
        return dict.__delitem__(self, key)
    
    def __setitem__(self, key, value, /):
        with POVPrint.attr() as printer:
            printer.print(self._name, '[', POVPrint.value(key), ']', ":=", POVPrint.value(value))
        return dict.__setitem__(self, key, value)
    
    def __ior__(self, rhs, /):
        with POVPrint.attr() as printer:
            printer.print(self._name, "|=")
            rhs = dict(rhs)
            for k, v in rhs:
                printer.print('\t', POVPrint.value(k), "=>", POVPrint.value(v))
        return dict.__ior__(self, rhs)

    def clear(self, /):
        with POVPrint.attr() as printer:
            printer.print(self._name, 'cleared')
        return dict.clear(self)
    
    def get(self, key, default=None, /):
        if key not in self:
            with POVPrint.attr() as printer:
                printer.print(self._name, 'get(', POVPrint.value(key), ') missed',
                             "=>", POVPrint.value(default))
        return dict.get(self, key, default)
    
    def pop(self, key, default=None, /):
        had = key in self
        value = dict.pop(self, key, default)
        with POVPrint.attr() as printer:
            printer.print(self._name, "pop(", POVPrint.value(key), ')',
                        self.cons.info("<miss>" if not had else "<hit>"),
                        "=>", POVPrint.value(value))
        return value
    
    def popitem(self, /):
        k, v = dict.popitem(self)
        with POVPrint.attr() as printer:
            printer.print(self._name, "popitem", "=>",
                         '(', POVPrint.value(k), ',', POVPrint.value(v), ')')
        return k, v
    
    def setdefault(self, key, default=None, /):
        had = key in self
        value = dict.setdefault(self, key, default)
        with POVPrint.attr() as printer:
            printer.print(self._name, "setdefault(", POVPrint.value(key), "=>", POVPrint.value(value),
                         self.cons.info("<no update>" if had else "<updated>"))
        return value
    
    def update(self, *args, **kwargs):
        with POVPrint.attr() as printer:
            printer.print(self._name, "update:")
            for arg in args:
                arg = dict(arg)
                for key in arg:
                    val = arg[key]
                    printer.print('\t', POVPrint.value(key), "=>", POVPrint.value(val))
            for kw in kwargs:
                val = kwargs[kw]
                printer.print('\t', POVPrint.value(key), "=>", POVPrint.value(val))
        return dict.update(self, *args, **kwargs)

class POVList(POVObj, list):
    
    def __init__(self, *args, pov_name="POVList", **kwargs):
        list.__init__(self, *args, **kwargs)
        POVObj.__init__(self, pov_name, list)
    
    def __delitem__(self, key, /):
        with POVPrint.attr() as printer:
            printer.print("del", self._name, '[', POVPrint.const(key), ']')
        return list.__delitem__(self, key)
    
    def __iadd__(self, rhs, /):
        rhs = list(rhs)
        with POVPrint.attr() as printer:
            printer.print(self._name, "+=")
            for it in rhs:
                printer.print('\t', POVPrint.value(it))
        return list.__iadd__(self, rhs)
    
    def __imul__(self, mul, /):
        with POVPrint.attr() as printer:
            printer.print(self._name, "*=", POVPrint.value(mul))
        return list.__imul__(self, mul)
    
    def __setitem__(self, index, value, /):
        with POVPrint.attr() as printer:
            printer.print(self._name, '[', POVPrint.const(index), ']', ":=", POVPrint.value(value))
        return list.__setitem__(self, index, value)
    
    def append(self, obj, /):
        with POVPrint.attr() as printer:
            printer.print(self._name, "append(", POVPrint.value(obj), ")")
        return list.append(self, obj)

    def clear(self, /):
        with POVPrint.attr() as printer:
            printer.print(self._name, "cleared")
        return list.clear(self)
    
    def insert(self, index, obj, /):
        with POVPrint.attr() as printer:
            printer.print(self._name, "insert", POVPrint.value(obj),
                         "at index", POVPrint.const(index))
        return list.insert(self, index, obj)
    
    def pop(self, index=-1, /):
        value = list.pop(self, index)
        with POVPrint.attr() as printer:
            printer.print(self._name, f"pop(", POVPrint.const(index), ")", "=>", POVPrint.value(value))
        return value
    
    def remove(self, obj, /):
        with POVPrint.attr() as printer:
            printer.print(self._name, "removing", POVPrint.value(obj))
        return list.remove(self, obj)

    def reverse(self, /):
        with POVPrint.attr() as printer:
            printer.print(self._name, "in-place reversal")
        return list.reverse(self)
    
    def sort(self, *, key=None, reverse=False):
        with POVPrint.attr() as printer:
            printer.print(self._name, "sorted")
        return list.sort(self, key=key, reverse=reverse)

##### Front-end API #####


def print_to(file):
    """
    POVPrint_to interface
    """
    return POV().print_to(file)

def info(*args, **kwargs):
    """
    POV.info interface
    """
    return POV().info(*args, **kwargs)

def ok(*args, **kwargs):
    """
    POV.ok interface
    """
    return POV().ok(*args, **kwargs)

def bad(*args, **kwargs):
    """
    POV.bad interface
    """
    return POV().bad(*args, **kwargs)

def warn(*args, **kwargs):
    """
    POV.warn interface
    """
    return POV().warn(*args, **kwargs)

def view(*exprs):
    """
    POV.view interface
    """
    return POV().view(*exprs)

def check(*exprs, exit_on_failure=False, interact_on_failure=False):
    """
    POV.check interface
    """
    return POV().check(*exprs, exit_on_failure=exit_on_failure, interact_on_failure=interact_on_failure)

def interact(normal_exit=False, normal_quit=True):
    """
    POV.interact interface
    """
    return POV().interact(normal_exit=normal_exit, normal_quit=normal_quit)

def track_attr(obj, *attrs):
    """
    POV.track_attr interface
    """
    return POV().track_attr(obj, *attrs)

def track_memfun(obj, function):
    """
    POV.track_memfun interface
    """
    return POV().track_memfun(obj, function)

def track(target=None, *, name=None, attrs=()):
    """
    POV.track interface
    """
    return POV().track(target, name=name, attrs=attrs)

def _pov_excepthook(exctype, value, tb):
    pov = POV()
    pov._log = []
    with POVPrint.bad() as printer:
        printer.print(POVPrint.head(f"Terminated with uncaught {exctype.__name__}"))
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
                
                printer.print(POVPrint.join(':', POVPrint.path(co.co_filename), POVPrint.info(line)),
                                POVPrint.func(func))
                if src:
                    printer.print('\t', POVPrint.expr(src))

            tb = tb.tb_next
        
        printer.print(POVPrint.exception(value))
        exit(-1)

sys.__excepthook__ = _pov_excepthook
sys.excepthook = _pov_excepthook
