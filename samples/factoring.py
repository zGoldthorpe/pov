"""
Demonstrates wrapper-based class tracking

Assumes "pov" is in PYTHONPATH
"""

@__import__("pov").stack(None).track(attrs=all)
class Factors:

    def __init__(self, *ns):
        self._prime_factors = {}
        for n in ns:
            self._append_factors(n)
    
    def _append_factors(self, n):
        k = 2
        while n > 1:
            while n % k == 0:
                n //= k
                self._prime_factors.setdefault(k, 0)
                self._prime_factors[k] += 1
            k += 1
    
    def factor_exponents(self, recursive=False):
        for p, e in self._prime_factors.items():
            if e == 1:
                continue
            if not isinstance(e, Factors):
                self._prime_factors[p] = Factors(e)
            if recursive:
                self._prime_factors[p].factor_exponents(True)
    
    def __repr__(self):
        if not self._prime_factors:
            return "1"
        return "(%s)" % " * ".join(f"{p}**{e}" for p, e in self._prime_factors.items())
    
    @property
    def value(self):
        return eval(repr(self))
    
    @staticmethod
    def about():
        return "This function factorises a product-list of numbers."
    
if __name__ == "__main__":
    fac = Factors(16, 625, 39, 39)

    print("About:", fac.about())
    print("Factors:", fac)

    fac.factor_exponents(True)
    print("Factored, recursively", fac)

    print("Value:", fac.value)