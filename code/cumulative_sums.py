# cumulative_sums_test.py
import math
from monobit import erfc

def normcdf(n):
    # Using the erfc approximation imported from monobit.py
    return 0.5 * erfc(-n * math.sqrt(0.5))

def p_value(n, z):
    sum_a = 0.0
    startk = int(math.floor((((float(-n)/z)+1.0)/4.0)))
    endk   = int(math.floor((((float(n)/z)-1.0)/4.0)))
    for k in range(startk, endk+1):
        c = (((4.0*k)+1.0)*z)/math.sqrt(n)
        d = normcdf(c)
        c = (((4.0*k)-1.0)*z)/math.sqrt(n)
        e = normcdf(c)
        sum_a = sum_a + d - e

    sum_b = 0.0
    startk = int(math.floor((((float(-n)/z)-3.0)/4.0)))
    endk   = int(math.floor((((float(n)/z)-1.0)/4.0)))
    for k in range(startk, endk+1):
        c = (((4.0*k)+3.0)*z)/math.sqrt(n)
        d = normcdf(c)
        c = (((4.0*k)+1.0)*z)/math.sqrt(n)
        e = normcdf(c)
        sum_b = sum_b + d - e

    p = 1.0 - sum_a + sum_b
    return p

def cumulative_sums_test(bits):
    n = len(bits)

    # Memory optimization: Compute partial sums directly without
    # duplicating the bits into a new list of +1/-1 values.
    pos = 0
    forward_max = 0
    for bit in bits:
        e = 1 if bit == 1 else -1
        pos = pos + e
        if abs(pos) > forward_max:
            forward_max = abs(pos)

    pos = 0
    backward_max = 0
    for bit in reversed(bits):
        e = 1 if bit == 1 else -1
        pos = pos + e
        if abs(pos) > backward_max:
            backward_max = abs(pos)

    # Step 4
    p_forward  = p_value(n, forward_max)
    p_backward = p_value(n, backward_max)

    success = ((p_forward >= 0.01) and (p_backward >= 0.01))
    plist = [p_forward, p_backward]

    return (success, None, plist)
