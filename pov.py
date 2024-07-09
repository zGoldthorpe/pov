"""
POV module

Glorified printing functionality
"""

import code
import inspect
import sys

_in_pov = False # flag to avoid nested pov calls

def _print_frame(stacklimit, file, _pov_depth):
    """
    Print some amount of the current call stack.

    stacklimit: how many levels up to print the stack (from _pov_depth)
                e.g. stacklimit=1 prints only the caller
    file:       print output file
    _pov_depth: depth of call stack to ignore (because of entry into this module)

    Returns full stack after _pov_depth
    """
    stack = inspect.stack()[_pov_depth:]
    stack_range = range(stacklimit if stacklimit else len(stack))
    for frame, _ in reversed(list(zip(stack, stack_range))):
        print(f"[s] {frame.filename}:{frame.lineno} ({frame.function})", file=file)
    
    return stack

def log(*args, stacklimit=1, file=sys.stderr, _pov_depth=1, **kwargs):
    """
    Simple log printing; behaves like an ordinary print
    """
    global _in_pov
    if _in_pov:
        return
    
    _print_frame(stacklimit, file, _pov_depth+1)

    print(f"[l]", *args, **kwargs, file=file)

def view(*exprs, heading=None, stacklimit=1, file=sys.stderr, interact=False, exitpt=False, _pov_depth=1):
    """
    View the values of various expressions.
    Note that if the expressions have effects when computed, these effects will persist
    in the real program.

    exprs:      strings of expressions to parse
    heading:    initial message before viewing expressions
    stacklimit: how many levels up to print the stack context (default: 1)
    file:       output file of prints (default: stderr)
    interact:   after viewing, enter interactive mode (default: False)
    exitpt:     after viewing, exit program (default: False)
    """
    global _in_pov
    if _in_pov:
        return

    _in_pov = True
    stack = _print_frame(stacklimit, file, _pov_depth+1)
    frame = stack[0].frame
    context = dict(frame.f_locals, **frame.f_globals)
    if heading is not None:
        print("[i]", heading, file=file)
    for expr in exprs:
        if not isinstance(expr, str):
            print("[+]", expr, sep='\t', file=file)
            continue
        try:
            val = eval(expr, context)
            print(f"[+]\t{expr}", "=>", val, "::", type(val).__name__, file=file)
        except Exception as e:
            print(f"[-]\t{expr}", "><", type(e).__name__, "::", e, file=file)
    
    if interact:
        code.interact(banner="[i] Entering interactive mode."
                            " Press Ctrl-D to exit and continue program execution."
                            " Or, type exit() to terminate the program.",
                        local=context
                      )

    if exitpt:
        print(f"[x] Exiting...")
        exit()
    _in_pov = False