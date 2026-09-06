from math import e

_a =    ( 1.00000000000000000000, 0.57721566490153286061, -0.65587807152025388108,
         -0.04200263503409523553, 0.16653861138229148950, -0.04219773455554433675,
         -0.00962197152787697356, 0.00721894324666309954, -0.00116516759185906511,
         -0.00021524167411495097, 0.00012805028238811619, -0.00002013485478078824,
         -0.00000125049348214267, 0.00000113302723198170, -0.00000020563384169776,
          0.00000000611609510448, 0.00000000500200764447, -0.00000000118127457049,
          0.00000000010434267117, 0.00000000000778226344, -0.00000000000369680562,
          0.00000000000051003703, -0.00000000000002058326, -0.00000000000000534812,
          0.00000000000000122678, -0.00000000000000011813, 0.00000000000000000119,
          0.00000000000000000141, -0.00000000000000000023, 0.00000000000000000002
       )

def gamma(x):
    y = float(x) - 1.0
    sm = _a[-1]

    # Zastępujemy _a[-2::-1] pętlą po indeksach, idąc od przedostatniego elementu do zerowego
    for i in range(len(_a) - 2, -1, -1):
        sm = sm * y + _a[i]

    return 1.0 / sm

def upper_incomplete_gamma(a, x, iterations=100):
    # Iteracyjne, odwrócone obliczanie ułamka łańcuchowego (bottom-up)
    if iterations % 2 == 1:
        val = 1.0
    else:
        m = iterations / 2.0
        val = x + (m - a)

    for d in range(iterations - 1, 0, -1):
        if d % 2 == 1:
            m = 1.0 + ((d - 1.0) / 2.0)
            val = x + (m - a) / val
        else:
            m = d / 2.0
            val = 1.0 + m / val

    try:
        result = ((x**a) * (e**(-x))) / val
    except OverflowError:
        result = 0.0

    return result

def gammaincc(a, x):
    return upper_incomplete_gamma(a, x) / gamma(a)
