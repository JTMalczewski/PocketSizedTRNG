period_between_lows = (
    0x2000,  # wait 0 pin 0
    0x2800,  # wait 1 pin 0
    0xE000,  # set x, 0
    0x0806,  # jmp pin, cont
    0x0008,  # jmp end
    0x1403,  # jmp x--, loop
    0xA001,  # mov isr, x
    0x8000,  # push
)
