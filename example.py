"""
Demonstrates simple class attribute tracking.

Assumes "pov" is in PYTHONPATH

Pass command-line arguments to enable debugging.
    'count' tracks CountAndTrack._count
    'track' tracks CountAndTrack._track
    'all' tracks all attributes
    'count_fun' tracks CountAndTrack.count()
    'fullstack' tracks the entire call stack (only for subsequent CL args)
"""
import sys

class CountAndTrack:

    def __init__(self):
        self._count = 0
        self._track = None
    
    def count(self, value):
        self._count += 1
        self._track = value
    
    def get_stats(self):
        return self._count, self._track
    
def naive_fibonacci(n:int, counter:CountAndTrack):
    result = n if n <= 1 \
        else naive_fibonacci(n-1, counter) + naive_fibonacci(n-2, counter)
    counter.count(result)
    return result

if __name__ == "__main__":
    for arg in sys.argv[1:]:
        match arg:
            case 'count':
                __import__("pov").track_attr(CountAndTrack, "_count")
            case 'track':
                __import__("pov").track_attr(CountAndTrack, "_track")
            case 'all':
                __import__("pov").track_attr(CountAndTrack, all)
            case 'count_fun':
                __import__("pov").track_memfun(CountAndTrack, "count")
            case 'fullstack':
                __import__("pov").stack(None, globally=True)
    
    counter = CountAndTrack()
    print("5th Fibonacci number:", naive_fibonacci(5, counter))
    count, track = counter.get_stats()
    print("Count:", count, "Track:", track)