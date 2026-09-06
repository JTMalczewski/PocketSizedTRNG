# monobit.py
import math

def count_ones_zeroes(bits):
    ones = 0
    zeroes = 0
    for bit in bits:
        if bit == 1:
            ones += 1
        else:
            zeroes += 1
    return zeroes, ones

def erfc(x):
    """
    Aproksymacja komplementarnej funkcji błędu (erfc)
    według wzoru Abramowitza i Steguna (7.1.26).
    Maksymalny błąd wynosi ~ 1.5 * 10^-7.
    """
    sign = 1 if x >= 0 else -1
    x = abs(x)

    # Stałe precyzji dla wielomianu
    p = 0.3275911
    a1 = 0.254829592
    a2 = -0.284496736
    a3 = 1.421413741
    a4 = -1.453152027
    a5 = 1.061405429

    t = 1.0 / (1.0 + p * x)

    # Horner's method dla lepszej wydajności obliczeń
    y = (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-x * x)

    return y if sign == 1 else 2.0 - y

def monobit_test(bits):
    n = len(bits)

    zeroes, ones = count_ones_zeroes(bits)
    s = abs(ones - zeroes)
    print("  Ones count   = %d" % ones)
    print("  Zeroes count = %d" % zeroes)

    # Wykorzystanie naszej lokalnej, zoptymalizowanej funkcji erfc
    p_val = erfc(float(s) / (math.sqrt(float(n)) * math.sqrt(2.0)))

    success = (p_val >= 0.01)
    return success, p_val, None
