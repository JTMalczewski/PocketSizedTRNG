# runs_test.py
import math
from monobit import erfc, count_ones_zeroes

def runs_test(bits):
    n = len(bits)
    if n < 100:
        print("Too little data for test. Supply at least 100 bits.")
        return False, 0.0, None

    # Calculate proportion of ones (pi) using the existing function from monobit.py
    zeroes, ones = count_ones_zeroes(bits)
    pi = float(ones) / float(n)

    # Prerequisite: Check if the sequence passes the proportion test
    tau = 2.0 / math.sqrt(n)
    if abs(pi - 0.5) >= tau:
        print("  Failed prerequisite proportion check.")
        return False, 0.0, None

    # Calculate V_obs (number of runs)
    v_obs = 1
    for i in range(n - 1):
        if bits[i] != bits[i+1]:
            v_obs += 1

    # Calculate p-value
    numerator = abs(v_obs - 2.0 * n * pi * (1.0 - pi))
    denominator = 2.0 * math.sqrt(2.0 * n) * pi * (1.0 - pi)

    # We use the erfc function imported from monobit.py
    p_val = erfc(numerator / denominator)

    success = (p_val >= 0.01)
    return success, p_val, None
