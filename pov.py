"""
POV module

Glorified printing functionality
"""

import code
import inspect
import sys

class _pov_printer:

    _print_queue = []
    _print_depth = 0

    def __init__(self, file):
        self._file = file

    def __enter__(self):
        _pov_printer._print_depth += 1
        self._print_queue = []
        return self
    
    def print(self, *args, **kwargs) -> None:
        kwargs["file"] = self._file
        self._print_queue.append((args, kwargs))
    
    def print_if(self, *args, **kwargs) -> None:
        if self.toplevel:
            self._print(*args, **kwargs)
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        _pov_printer._print_depth -= 1
        _pov_printer._print_queue.extend(self._print_queue)
        
        if _pov_printer._print_depth == 0:
            for args, kwargs in _pov_printer._print_queue:
                print(*args, **kwargs)
            _pov_printer._print_queue.clear()
    
    @property
    def toplevel(self) -> bool:
        return _pov_printer._print_depth == 1

class POV:

    def __init__(self, *, stacklimit=1, file=sys.stderr, _pov_depth=1):
        """
        Initialisation parameters:
        stacklimit: how many levels of stack context to print (None for no limit)
                    (default: 1)
        file:       print output file
                    (default: stderr)
        """
        self._stack = inspect.stack()[_pov_depth:]
        self._file = file
        stackrange = range(stacklimit if stacklimit else len(self._stack))
        self._traceback = []
        for frame, _ in reversed(list(zip(self._stack, stackrange))):
            self._traceback.append(f"{frame.filename}:{frame.lineno} ({frame.function})")
    
    def _print_tb(self, printer:_pov_printer) -> None:
        for tb in self._traceback:
            printer.print("[/]", tb)
    
    def _get_context(self):
        frame = self._stack[0].frame
        return dict(frame.f_locals, **frame.f_globals)

    def log(self, *args, **kwargs):
        """
        Simple logger; behaves like an ordinary print.
        """
        with _pov_printer(self._file) as printer:
            self._print_tb(printer)
            printer.print(f"[i]", *args, **kwargs)

        return self
    
    def view(self, *exprs : str):
        """
        View the value of various expressions.
        """

        with _pov_printer(self._file) as printer:
            self._print_tb(printer)
            context = self._get_context()
            
            for expr in exprs:
                if not isinstance(expr, str):
                    printer.print("[+]", expr, sep='\t')
                    continue
                try:
                    val = eval(expr, context)
                    printer.print(f"[+]\t{expr}", "=>", val, "::", type(val).__name__)
                except Exception as e:
                    printer.print(f"[-]\t{expr}", "><", type(e).__name__, "::", e)

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
        
        code.interact(banner="[i] Entering interactive mode.\n"
                                + msg,
                        local=context)


def log(*args, stacklimit=1, file=sys.stderr, _pov_depth=1, **kwargs):
    """
    POV.log interface
    """
    return POV(stacklimit=stacklimit, file=file, _pov_depth=_pov_depth+1).log(*args, **kwargs)

def view(*exprs, stacklimit=1, file=sys.stderr, _pov_depth=1):
    """
    POV.view interface
    """
    return POV(stacklimit=stacklimit, file=file, _pov_depth=_pov_depth+1).view(*exprs)