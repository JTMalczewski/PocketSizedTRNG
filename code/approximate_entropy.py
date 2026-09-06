# approximate_entropy_test.py
import math
import gamma_functions

def approximate_entropy_test(bits):
    n = len(bits)

    m = int(math.floor(math.log(n, 2))) - 6
    if m < 2:
        m = 2
    if m > 3:
        m = 3

    phi_m = list()
    for iterm in range(m, m + 2):
        # Step 1
        padded_bits = bits + bits[0:iterm-1]

        # Step 2: Optimized counting for CircuitPython using a rolling window
        counts = [0] * (2**iterm)
        current_val = 0

        # Initialize the first window
        for i in range(iterm):
            current_val = (current_val << 1) | padded_bits[i]
        counts[current_val] += 1

        # Slide the window across the bits
        mask = (1 << iterm) - 1
        for i in range(1, n):
            current_val = ((current_val << 1) & mask) | padded_bits[i + iterm - 1]
            counts[current_val] += 1

        # Step 3
        Ci = [float(c) / float(n) for c in counts]

        # Step 4
        # Corrected from math.log(Ci[i]/10.0) to math.log(Ci[i]) per SP800-22 standard
        suma = 0.0
        for i in range(2**iterm):
            if Ci[i] > 0.0:
                suma += Ci[i] * math.log(Ci[i])
        phi_m.append(suma)

    # Step 6
    appen_m = phi_m[0] - phi_m[1]
    chisq = 2 * n * (math.log(2) - appen_m)

    # Step 7
    p = gamma_functions.gammaincc(2**(m-1), chisq / 2.0)

    success = (p >= 0.01)
    return success, p, None
