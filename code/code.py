# SPDX-FileCopyrightText: 2017 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import board
import busio
import rp2pio
import storage
import sdcardio
import array
from adafruit_pcf8523.pcf8523 import PCF8523
import digitalio
import sys
import usb_cdc
import monobit
import frequency_within_block
import runs
import longest_run
import serial
import approximate_entropy
import cumulative_sums
import HashDRBGMicro

# -------- Settings --------
VON_NEUMANN = True
WRITING = False
TRNG = True
TRNG_WRITING = False
LOGFILE = "/sd/Izotop_test_02_08_2026.csv"
TRNG_BIN_FILE = "/sd/TRND.bin"
CALIBRATION = False
BITS_TO_EXTRACT = 32

# -------- Test Settings --------
# TEST_MODE options:
# "NONE"     -> Tests disabled, data flows immediately without blocking.
# "INTERVAL" -> Run tests periodically every TEST_INTERVAL_BYTES generated.
# "RESEED"   -> Run tests every time before DRBG is instantiated or reseeded.
TEST_MODE = "RESEED"
TEST_INTERVAL_BYTES = 10000
N_BITS_TO_CHECK = 1000

# -------- DRBG settings --------
USE_DRBG = True
DRBG_ENTROPY_REQUIRED = 55
DRBG_OUTPUT_BYTES = 1024
PERSONALIZATION_STRING = b"Izotop_RP2040_TRNG_v1"
RESEED_INTERVAL = 1000

# -------- SD Card --------
SD_CS = board.GP17
spi = busio.SPI(board.GP18, board.GP19, board.GP16)
sdcard = sdcardio.SDCard(spi, SD_CS)
vfs = storage.VfsFat(sdcard)

if WRITING or TRNG_WRITING:
    try:
        storage.mount(vfs, "/sd")
        print("sd card mounted")
    except ValueError:
        print("no SD card")

# -------- Time --------
I2C = busio.I2C(board.GP5, board.GP4)
rtc = PCF8523(I2C)
set_time = False
t = rtc.datetime
days = ("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")
if set_time:   # change to True if you want to write the time!
    #                     year, mon, date, hour, min, sec, wday, yday, isdst
    t = time.struct_time((2025,  12,   9,   22,  33,  25,    1,   -1,    -1))

    print("Setting time to:", t)
    rtc.datetime = t
    print()

def rtc_timestamp(rtc):
    t = rtc.datetime
    return (
        f"{t.tm_year:04d}-{t.tm_mon:02d}-{t.tm_mday:02d},"
        f"{t.tm_hour:02d}:{t.tm_min:02d}:{t.tm_sec:02d}"
    )

# -------- Logs --------
#  initial write to the SD card on startup
if WRITING:
    try:
        with open("/sd/temp.txt", "a") as f:
            f.write('The date is {} {}/{}/{}\n'.format(days[t.tm_wday], t.tm_mon, t.tm_mday, t.tm_year))
            f.write('Start time: {}:{}:{}\n'.format(t.tm_hour, t.tm_min, t.tm_sec))
            f.write('Temp,Time\n')
            print("initial write to SD card complete, starting to log")
    except ValueError:
        print("initial write to SD card failed - check card")


# -------- Gaiger Configuration --------
period_between_lows_bin = array.array("H", [
    0xa02b, # 0: mov x, !null
    # --- MAIN LOOP ---
    0x00c6, # 1: jmp pin, 6

    # --- IF LOW SIGNAL DETECTED ---
    0xa0c1, # 2: mov isr, x
    0x8020, # 3: push
    0xa02b, # 4: mov x, !null
    0x20a0, # 5: wait 1 pin 0

    # --- COUNTING ---
    0x0041, # 6: jmp x--, 1
])

# - For 100 MHz (1 loop = 1 us)
# - unsigned 32-int counter: 4294967294
# - one loop takes 2 clock ticks
# - overflow after 86 s

measure = rp2pio.StateMachine(
    period_between_lows_bin,
    frequency=100_000_000,
    first_in_pin=board.GP0,
    jmp_pin=board.GP0,
    in_pin_count=1
)

buf = array.array("I", [0])

# -------- TRNG --------
_entropy_byte = 0
_bit_count = 0
_vn_prev_cycles = None

def get_entropy_bytes_and_bits(cycles, num_bits):
    global _entropy_byte, _bit_count, _vn_prev_cycles
    completed_bytes = []
    valid_bits = []

    if VON_NEUMANN:
        if _vn_prev_cycles is None:
            _vn_prev_cycles = cycles
        else:
            for i in range(num_bits):
                b1 = (_vn_prev_cycles >> i) & 1
                b2 = (cycles >> i) & 1

                valid_bit = None
                if b1 == 0 and b2 == 1:
                    valid_bit = 0
                elif b1 == 1 and b2 == 0:
                    valid_bit = 1

                if valid_bit is not None:
                    _entropy_byte = (_entropy_byte << 1) | valid_bit
                    _bit_count += 1
                    valid_bits.append(valid_bit)

                    if _bit_count == 8:
                        completed_bytes.append(_entropy_byte)
                        _entropy_byte = 0
                        _bit_count = 0

            _vn_prev_cycles = None
    else:
        for i in range(num_bits):
            bit = (cycles >> i) & 1
            _entropy_byte = (_entropy_byte << 1) | bit
            _bit_count += 1
            valid_bits.append(bit)

            if _bit_count == 8:
                completed_bytes.append(_entropy_byte)
                _entropy_byte = 0
                _bit_count = 0

    return completed_bytes, valid_bits


def run_all_tests(bits_to_test):
    print(f"\n--- Running tests ({len(bits_to_test)} bits) ---")

    success_mb, p, _ = monobit.monobit_test(bits_to_test)
    print(f"-> Monobit Result: {'PASSED' if success_mb else 'FAILED'} (p-value: {p:.5f})")

    success_blk, p_blk, _ = frequency_within_block.frequency_within_block_test(bits_to_test)
    print(f"-> Freq Within Block Result: {'PASSED' if success_blk else 'FAILED'} (p-value: {p_blk:.5f})")

    success_runs, p_runs, _ = runs.runs_test(bits_to_test)
    print(f"-> Runs Result: {'PASSED' if success_runs else 'FAILED'} (p-value: {p_runs:.5f})")

    success_lr, p_lr, _ = longest_run.longest_run_ones_in_a_block_test(bits_to_test)
    print(f"-> Longest Run Result: {'PASSED' if success_lr else 'FAILED'} (p-value: {p_lr:.5f})")

    success_serial, _, p_list_serial = serial.serial_test(bits_to_test)
    print(f"-> Serial Result: {'PASSED' if success_serial else 'FAILED'} (P1: {p_list_serial[0]:.5f}, P2: {p_list_serial[1]:.5f})")

    success_ae, p_ae, _ = approximate_entropy.approximate_entropy_test(bits_to_test)
    print(f"-> Approx Entropy Result: {'PASSED' if success_ae else 'FAILED'} (p-value: {p_ae:.5f})")

    success_cusum, _, p_list_cusum = cumulative_sums.cumulative_sums_test(bits_to_test)
    print(f"-> Cumulative Sums Result: {'PASSED' if success_cusum else 'FAILED'} (Fwd: {p_list_cusum[0]:.5f}, Bwd: {p_list_cusum[1]:.5f})")

    print("-----------------------------------------\n")
    return (success_mb and success_blk and success_runs and success_lr and
            success_serial and success_ae and success_cusum)

# -------- TRNG Calibration --------
if CALIBRATION:
    print("Starting calibration - counting pulses for 10 seconds (RTC)...")
    total_cycles = 0
    counts = 0

    while measure.in_waiting:
        measure.readinto(buf)

    start_time = time.mktime(rtc.datetime)
    current_time = start_time

    while (current_time - start_time) < 10:
        if measure.in_waiting:
            measure.readinto(buf)
            raw_value = buf[0]
            max_uint32 = 0xFFFFFFFF
            total_cycles += (max_uint32 - raw_value)
            counts += 1
        else:
            current_time = time.mktime(rtc.datetime)

    if counts > 0:
        avg_cycles = total_cycles // counts
        print(f"Calibration finished. {counts} pulses recorded.")
        print(f"Average number of cycles between pulses: {avg_cycles}")
    else:
        avg_cycles = 100_000_000
        print("No pulses during calibration. Assuming background radiation.")

    if avg_cycles < 50_000:
        BITS_TO_EXTRACT = 6
    elif avg_cycles < 500_000:
        BITS_TO_EXTRACT = 6
    elif avg_cycles < 5_000_000:
        BITS_TO_EXTRACT = 8
    else:
        BITS_TO_EXTRACT = 8

    print(f"Set to extract {BITS_TO_EXTRACT} bits from each read.")
else:
    print(f"Calibration skipped. Defaulted to {BITS_TO_EXTRACT} bits extraction.")

# -------- DRBG Setup --------
if USE_DRBG:
    drbg = HashDRBGMicro.HashDRBGMicro()
drbg_is_seeded = False
raw_entropy_buffer = bytearray(DRBG_ENTROPY_REQUIRED)
entropy_index = 0

# -------- Main State --------
log_buffer = ""
trng_buffer = bytearray()
last_save_time = time.monotonic()
SAVE_INTERVAL = 5.0

# Testing state variables
testing_active = False
bytes_since_last_test = 0
reseed_test_passed = False
test_bit_buffer = []

if WRITING:
    try:
        with open(LOGFILE, "a") as f:
            if f.tell() == 0:
                f.write("date,time,cycles,delta_ns\n")
    except Exception as e:
        print("SD init error for CSV:", e)

if TRNG_WRITING:
    print("Writing TRNG bytes to BIN file activated.")

print("I'm starting to collect data...")

while True:
    if measure.in_waiting:
        measure.readinto(buf)
        raw_value = buf[0]
        max_uint32 = 0xFFFFFFFF
        cycles = (max_uint32 - raw_value)

        new_bytes = []
        new_bits = []
        if TRNG or TRNG_WRITING or USE_DRBG:
            new_bytes, new_bits = get_entropy_bytes_and_bits(cycles, BITS_TO_EXTRACT)

        if WRITING:
            delta_ns = cycles * 20
            ts = rtc_timestamp(rtc)
            log_buffer += f"{ts},{cycles},{delta_ns}\n"

        # Evaluate if we need to trigger the testing phase
        if TEST_MODE == "INTERVAL":
            if bytes_since_last_test >= TEST_INTERVAL_BYTES:
                testing_active = True
        elif TEST_MODE == "RESEED":
            drbg_needs_seed = USE_DRBG and (not drbg_is_seeded or drbg.reseed_counter >= RESEED_INTERVAL)
            if drbg_needs_seed and not reseed_test_passed:
                testing_active = True
        else: # "NONE"
            testing_active = False

        # If testing phase is active, divert entropy strictly to the test buffer
        if testing_active:
            test_bit_buffer.extend(new_bits)
            if len(test_bit_buffer) >= N_BITS_TO_CHECK:
                bits_to_test = test_bit_buffer[:N_BITS_TO_CHECK]
                del test_bit_buffer[:N_BITS_TO_CHECK]

                all_passed = run_all_tests(bits_to_test)

                if all_passed:
                    print("-> ALL TESTS PASSED. Resuming output...\n")
                    testing_active = False
                    if TEST_MODE == "INTERVAL":
                        bytes_since_last_test = 0
                    elif TEST_MODE == "RESEED":
                        reseed_test_passed = True
                else:
                    print("-> TESTS FAILED. Collecting a new sample...\n")
                    test_bit_buffer = [] # Reset and test next chunk

            # Skip output routing while testing is gathering bits
            pass

        else:
            # We are NOT testing - securely route the stream out
            if TEST_MODE == "INTERVAL":
                bytes_since_last_test += len(new_bytes)

            valid_bytes = new_bytes

            if valid_bytes and (TRNG or TRNG_WRITING or USE_DRBG):
                bytes_to_export = valid_bytes

                if USE_DRBG:
                    for b in valid_bytes:
                        if entropy_index < DRBG_ENTROPY_REQUIRED:
                            raw_entropy_buffer[entropy_index] = b
                            entropy_index += 1

                    bytes_to_export = b"" # Suppress output until the DRBG triggers
                    needs_reseed = drbg_is_seeded and (drbg.reseed_counter >= RESEED_INTERVAL)

                    if (not drbg_is_seeded) or needs_reseed:
                        if entropy_index >= DRBG_ENTROPY_REQUIRED:
                            seed_chunk = bytes(raw_entropy_buffer)
                            entropy_index = 0

                            if not drbg_is_seeded:
                                rtc_nonce = rtc_timestamp(rtc).encode('utf-8')
                                drbg.instantiate(seed_chunk, rtc_nonce, PERSONALIZATION_STRING)
                                drbg_is_seeded = True
                            else:
                                drbg.reseed(seed_chunk)

                            # Reset reseed test requirement for the next time it's needed
                            reseed_test_passed = False

                    if drbg_is_seeded:
                        bytes_to_export = drbg.generate(DRBG_OUTPUT_BYTES)

                if TRNG and bytes_to_export:
                    if usb_cdc.data:
                        usb_cdc.data.write(bytes(bytes_to_export))

                if TRNG_WRITING and bytes_to_export:
                    trng_buffer.extend(bytes_to_export)

        # Continual SD Card flushing check
        if WRITING or TRNG_WRITING:
            current_time = time.monotonic()
            if (current_time - last_save_time) >= SAVE_INTERVAL:
                if WRITING and log_buffer:
                    try:
                        with open(LOGFILE, "a") as f:
                            f.write(log_buffer)
                        log_buffer = ""
                        print('CSV Buffer saved')
                    except Exception as e:
                        print(f"Error saving CSV to SD: {e}")

                if TRNG_WRITING and trng_buffer:
                    try:
                        with open(TRNG_BIN_FILE, "ab") as f:
                            f.write(trng_buffer)
                        trng_buffer = bytearray()
                        print('TRNG Buffer saved')
                    except Exception as e:
                        print(f"Error saving BIN to SD: {e}")

                last_save_time = current_time

    time.sleep(0.001)
