"""
Demonstrates wrapper-based function tracking

Assumes "pov" is in PYTHONPATH
"""
@__import__("pov").stack(None).track
def binom(n, k, mem={}):
    if not 0 <= k <= n:
        return 0
    if k == 0 or k == n:
        return 1
    if (n, k) not in mem:
        mem[n, k] = binom(n-1, k-1, mem) + binom(n-1, k, mem)
    return mem[n, k]

if __name__ == "__main__":
    print("10 choose 5 =", binom(10, 5))