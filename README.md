# POV
Python Object Viewer

The purpose of this module is to provide some "debugging utilities" for probing/studying large Python projects (that you have full access to) with minimal code injection.
There's nothing fancy here; it's essentially a glorification of littering the codebase with `print("Here!")` statements.

### Intended usage

Add `pov` folder to your Python path

(Linux bash)
```bash
export PYTHONPATH=$PYTHONPATH:/path/to/pov
```

(Windows powershell)
```powershell
$env:PYTHONPATH+=";/path/to/pov"
$env:ANSICON=1                      # for coloured console output
```

Then, you can inject POV debug messages in individual lines using, e.g.

```python
__import__("pov").info("Hello world!")
# ...
def foo(x, y, z):
    # ...
    __import__("pov").view("x.bar", "y.baz()")
    # ...
```

See `samples/` for example uses.

### Parameters

By default, POV will wrap Python's default exception hooks.
This can be controlled through the environment variable `POV_KEEP_EXCEPTHOOK`: set to `1` to use Python's normal exception hooks.

POV also wraps Python's builtin `print` function to match with POV's output style.
This can be controlled through the environment variable `POV_KEEP_PRINT`: set to `1` to use Python's normal `print` function.

To completely disable POV, use the environment `POV_DISABLE`.
To instead direct POV output to a file (from the command line), use the environment `POV_FILE`.

At startup, you can also have POV print environment variable values by populating `POV_ENV` with a space-separated list of environment variable names.

### Object view depth

The depth and detail at which objects are probed (e.g., with `pov.view()`) can be managed at runtime with the `pov.detail(depth, *, full, globally)` function.
- `depth` controls how many layers deep into the object's attributes we dig (the default depth is 2 layers).
Set to `-1` if you want no depth limit (though this may lead to unbounded recursion, so this is **not** recommended).
- `full` is a boolean that indicates if private attributes should also be probed.
- `globally` is a boolean that indicates if these parameters should be applied to the current `POV` instance, or to the entire program.

These parameters can be controlled globally through environment variables:
- `depth` can be controlled with `POV_DEPTH`.
- `full` can be controlled with `POV_FULL`.

### Filtering POV calls

POV functions can also be decorated with an integer ID using square brackets.
By default, all functions have ID `0`.
For example:

```python
__import__("pov").info[1000]("Hello world!")
# ...
@__import__("pov").track[20]
def foo(x, y, z):
    # ...
    __import__("pov").view[1]("x.bar").view[5]("y.baz()")
    # ...
```

Which priority values are visible can be controlled through the environment variable `POV_IDS`, which can be given a comma-separated list of integers or integer ranges.
Integer ranges are hyphen-separated pairs of integers.
Omitted values in a range denote that the range is unbounded on that side.

```bash
POV_IDS=1000        # only "Hello world!" is visible
POV_IDS=-           # everything is visible (this is the default); same as POV_IDS=0-
POV_IDS=1,1000      # "Hello world!" and "x.bar" are visible
POV_IDS=3-          # "Hello world!" and "y.baz()" are visible, and "foo" is tracked
POV_IDS=-100        # "x.bar" and "y.baz()" are visible, and "foo" is tracked; same as POV_IDS=0-100
POV_IDS=            # nothing is visible (*NOT* equivalent to setting POV_DISABLE=1)
```