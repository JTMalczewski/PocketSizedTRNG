#frequency_within_block.py
import math
import gamma_functions # Upewnij się, że plik gamma_functions.py znajduje się na Pico

def count_ones_zeroes(bits):
    ones = 0
    zeroes = 0
    for bit in bits:
        if (bit == 1):
            ones += 1
        else:
            zeroes += 1
    return (zeroes,ones)

def frequency_within_block_test(bits):
    n = len(bits)
    M = 20
    N = int(math.floor(n/M))
    if N > 99:
        N=99
        M = int(math.floor(n/N))

    if len(bits) < 100:
        print("Too little data for test. Supply at least 100 bits")
        return False,1.0,None

    print("  n = %d" % len(bits))
    print("  N = %d" % N)
    print("  M = %d" % M)

    num_of_blocks = N
    block_size = M

    proportions = list()
    for i in range(num_of_blocks):
        block = bits[i*(block_size):((i+1)*(block_size))]
        zeroes,ones = count_ones_zeroes(block)
        # Zmiana: standardowe dzielenie zamiast użycia obiektu Fraction
        proportions.append(ones / block_size)

    chisq = 0.0
    for prop in proportions:
        # Zmiana: użycie 0.5 zamiast Fraction(1,2)
        chisq += 4.0*block_size*((prop - 0.5)**2)

    p = gamma_functions.gammaincc((num_of_blocks/2.0),float(chisq)/2.0)
    success = (p >= 0.01)
    return (success,p,None)
