# POV
Python Object Viewer

The purpose of this module is to provide some "debugging utilities" for probing/studying large Python projects (that you have full access to) with minimal code injection.
There's nothing fancy here; it's essentially a glorification of littering the codebase with `print("Here!")` statements.

### Intended usage

Add `pov` folder to your Python path

```bash
export PYTHONPATH=$PYTHONPATH:/path/to/pov
```

Then, you can inject POV debug messages in individual lines using, e.g.

```python
__import__("pov").log("Hello world!")
# ...
def foo(x, y, z):
    # ...
    __import__("pov").view("x.bar", "y.baz()")
    # ...
```

See `samples/` for example uses.