"""
Demonstrates simple class dictionary attribute tracking.

Assumes "pov" is in PYTHONPATH

Pass command-line arguments to enable debugging.
    'memo' tracks memoisation table
    'get' tracks get method
"""
import sys

class Fibonacci:

    def __init__(self):
        self._memo = { 0 : 0, 1 : 1}
    
    def get(self, n:int):
        if n not in self._memo:
            self._memo[n] = self.get(n-1) + self.get(n-2)
        return self._memo[n]

if __name__ == "__main__":
    for arg in sys.argv[1:]:
        match arg:
            case 'memo':
                __import__("pov").track_attr(Fibonacci, "_memo")
            case 'get':
                __import__("pov").track_memfun(Fibonacci, "get")
    
    print("10th Fibonacci number:", Fibonacci().get(10))
