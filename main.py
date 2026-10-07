from bb84.module1_random_bits import generate_random_bits
from bb84.module2_random_basis import generate_random_bases
from bb84.module3_qubit_preparation import prepare_qubits
from bb84.quantum_channel import transmit
from bb84.bob_measurement import measure_qubits
from bb84.module5_sifting import sift_key
from bb84.module6_qber import calculate_qber
from bb84.module7_eve import eve_intercept_resend
from bb84.module10_qber_decision import qber_decision
from bb84.module8_error_correction import error_correction
from bb84.module9_privacy_amplification import privacy_amplification
from bb84.qcs_synchronization import (
    build_qcs_result,
    compare_detection_windows,
    filter_detected,
)
from visualize_bb84 import visualize_qubit
from encrypt_decrypt import encrypt, decrypt, text_to_bits


# How many items to show in previews (to avoid flooding terminal)
SHOW = 10


# =====================================================
# HELPER: print a section header
# =====================================================

def section(title):
    print()
    print("=" * 55)
    print(f"  {title}")
    print("=" * 55)


# =====================================================
# USER INPUT
# =====================================================

section("BB84 QUANTUM KEY DISTRIBUTION")

desired_key_length = 256

print()

while True:
    eve_choice = input("  Enable Eve (eavesdropper)? (y/n): ").strip().lower()
    if eve_choice in ("y", "n"):
        EVE = (eve_choice == "y")
        break
    else:
        print("  Invalid. Please enter y or n.")


# =====================================================
# PARAMETERS
# =====================================================

num_bits    = desired_key_length * 4
MAX_ATTEMPTS = 10
NOISE_RATE  = 0.03  # 3% natural channel noise

# QCS timing parameters. The offset is intentionally larger than the
# narrow detector windows so the unsynchronized case visibly fails.
CLOCK_PERIOD_NS = 10.0
PROPAGATION_DELAY_NS = 50.0
CLOCK_OFFSET_NS = 4.0
CLOCK_DRIFT_PPM = 40.0
TIMING_JITTER_NS = 0.35
ACTIVE_DETECTOR_WINDOW_NS = 2.0
DETECTOR_WINDOW_SIZES_NS = [0.5, 1.0, 2.0, 5.0, 8.0]
SYNC_SAMPLE_COUNT = 200

print()
print(f"  Desired final key length  : {desired_key_length} bits")
print(f"  Raw qubits Alice will send: {num_bits}")
print(f"  Channel Noise Rate        : {NOISE_RATE * 100}%")
print(f"  Eve                       : {'ON — partial interception (20%)' if EVE else 'OFF'}")
print(f"  Max attempts              : {MAX_ATTEMPTS}")
print(f"  QCS detector window       : {ACTIVE_DETECTOR_WINDOW_NS} ns")
print(f"  Clock offset to correct   : {CLOCK_OFFSET_NS} ns")
print(f"  Clock drift to correct    : {CLOCK_DRIFT_PPM} ppm")
print(f"  Timing jitter             : {TIMING_JITTER_NS} ns")


# =====================================================
# QCS DETECTION PROOF
# =====================================================

section("QUANTUM CLOCK SYNCHRONIZATION - DETECTION PROOF")

print()
print("  If Bob's clock is not synchronized, his detector gate opens")
print("  at the wrong time. The photon may arrive outside the gate,")
print("  so it is not detected and cannot contribute to the key.")
print()
print(f"  {'Window (ns)':>11}   {'No QCS Detected':>15}   {'No QCS %':>9}   {'With QCS Detected':>17}   {'With QCS %':>10}")
print(f"  {'-----------':>11}   {'---------------':>15}   {'--------':>9}   {'-----------------':>17}   {'----------':>10}")

window_rows = compare_detection_windows(
    num_qubits=num_bits,
    window_sizes_ns=DETECTOR_WINDOW_SIZES_NS,
    clock_period_ns=CLOCK_PERIOD_NS,
    propagation_delay_ns=PROPAGATION_DELAY_NS,
    clock_offset_ns=CLOCK_OFFSET_NS,
    clock_drift_ppm=CLOCK_DRIFT_PPM,
    timing_jitter_ns=TIMING_JITTER_NS,
    sync_sample_count=SYNC_SAMPLE_COUNT,
)

for row in window_rows:
    print(
        f"  {row['window_ns']:>11.1f}   "
        f"{row['unsynced_detected']:>15}/{num_bits:<4}   "
        f"{row['unsynced_pct']:>8.2f}%   "
        f"{row['synced_detected']:>17}/{num_bits:<4}   "
        f"{row['synced_pct']:>9.2f}%"
    )

print()
print("  Result: narrow detector windows need accurate synchronization.")
print("  With QCS, Bob recenters the detector gate and detects more photons.")


# =====================================================
# QUBIT CIRCUIT PREVIEW (first 5 only)
# =====================================================

PREVIEW_COUNT = 5

section(f"QUBIT CIRCUIT PREVIEW  (first {PREVIEW_COUNT} of {num_bits})")

preview_bits  = generate_random_bits(PREVIEW_COUNT)
preview_bases = generate_random_bases(PREVIEW_COUNT)

for i in range(PREVIEW_COUNT):
    visualize_qubit(
        bit=preview_bits[i],
        basis=preview_bases[i],
        qubit_number=i + 1
    )


# =====================================================
# RETRY LOOP  (minimal output per attempt)
# =====================================================

attempt        = 0
key_established = False

# Variables to hold data from the winning attempt
win_alice_bits  = win_alice_bases = win_alice_key  = None
win_bob_bases   = win_bob_bits    = win_bob_key    = None
win_intercepted = 0
win_qber        = 0
win_corrected   = win_final_key  = None
win_errors      = 0
win_qcs_result  = None
win_detected_count = 0

section("KEY ESTABLISHMENT — RETRY LOOP")
print()
print(f"  {'Attempt':>7}   {'Detected':>10}   {'Detect %':>8}   {'Sifted Bits':>11}   {'QBER':>7}   {'Decision':>15}")
print(f"  {'-------':>7}   {'--------':>10}   {'--------':>8}   {'-----------':>11}   {'----':>7}   {'--------':>15}")

while attempt < MAX_ATTEMPTS:

    attempt += 1

    # ----- Alice -----
    alice_bits  = generate_random_bits(num_bits)
    alice_bases = generate_random_bases(num_bits)
    qubits      = prepare_qubits(alice_bits, alice_bases)

    # ----- Quantum channel -----
    received_qubits = transmit(qubits, noise_rate=NOISE_RATE)

    # ----- Eve -----
    intercepted = 0
    if EVE:
        received_qubits, eve_bases, eve_bits, intercepted = eve_intercept_resend(
            received_qubits, interception_rate=0.2
        )

    # ----- Quantum Clock Synchronization -----
    qcs_result = build_qcs_result(
        num_qubits=num_bits,
        clock_period_ns=CLOCK_PERIOD_NS,
        propagation_delay_ns=PROPAGATION_DELAY_NS,
        clock_offset_ns=CLOCK_OFFSET_NS,
        clock_drift_ppm=CLOCK_DRIFT_PPM,
        timing_jitter_ns=TIMING_JITTER_NS,
        detector_window_ns=ACTIVE_DETECTOR_WINDOW_NS,
        sync_sample_count=SYNC_SAMPLE_COUNT,
    )
    detected_mask = qcs_result["synced_mask"]
    detected_count = sum(1 for detected in detected_mask if detected)
    detected_pct = qcs_result["synced_detection_pct"]

    if detected_count == 0:
        print(f"  {attempt:>7}   {detected_count:>10}   {detected_pct:>7.2f}%   {0:>11}   {'--':>6}   {'No photons detected':>15}")
        continue

    detected_alice_bits = filter_detected(alice_bits, detected_mask)
    detected_alice_bases = filter_detected(alice_bases, detected_mask)
    detected_qubits = filter_detected(received_qubits, detected_mask)

    if EVE:
        detected_eve_bases = filter_detected(eve_bases, detected_mask)
        detected_eve_bits = filter_detected(eve_bits, detected_mask)
    else:
        detected_eve_bases = None
        detected_eve_bits = None

    # ----- Bob -----
    bob_bases = generate_random_bases(detected_count)
    bob_bits  = measure_qubits(detected_qubits, bob_bases)

    # ----- Sifting -----
    alice_key, bob_key = sift_key(
        detected_alice_bits, detected_alice_bases, bob_bases, bob_bits
    )

    # ----- QBER -----
    qber          = calculate_qber(alice_key, bob_key)
    qber_ok       = qber_decision(qber)
    qber_pct      = round(qber * 100, 2)
    decision_text = "KEY ACCEPTED" if qber_ok else "QBER too high — retry"

    print(f"  {attempt:>7}   {detected_count:>10}   {detected_pct:>7.2f}%   {len(alice_key):>11}   {qber_pct:>6}%   {decision_text:>15}")

    if not qber_ok:
        continue

    # ----- Error correction -----
    corrected_key, num_errors = error_correction(alice_key, bob_key)

    # ----- Privacy amplification -----
    final_key = privacy_amplification(corrected_key, output_length=desired_key_length)

    # Save winning attempt data
    win_alice_bits  = detected_alice_bits
    win_alice_bases = detected_alice_bases
    win_alice_key   = alice_key
    win_bob_bases   = bob_bases
    win_bob_bits    = bob_bits
    win_bob_key     = bob_key
    win_eve_bases   = detected_eve_bases
    win_eve_bits    = detected_eve_bits
    win_intercepted = intercepted
    win_qber        = qber
    win_errors      = num_errors
    win_corrected   = corrected_key
    win_final_key   = final_key
    win_qcs_result  = qcs_result
    win_detected_count = detected_count

    key_established = True
    break


# =====================================================
# SESSION ABORTED
# =====================================================

if not key_established:
    section("SESSION ABORTED")
    print()
    print(f"  Total attempts : {attempt}")
    print()
    print("  QBER stayed above 11% across all attempts.")
    print("  Persistent eavesdropper detected.")
    print("  No key established. Communication unsafe.")
    exit()


# =====================================================
# KEY ESTABLISHED — SHOW FULL DETAIL
# =====================================================

section("KEY ESTABLISHMENT — DETAILED RESULTS")

print()
print("  Quantum Clock Synchronization (QCS)")
print("  " + "=" * 95)
print()
print(f"  Detector window used             : {win_qcs_result['detector_window_ns']} ns")
print(f"  Unsynchronized detection         : {win_qcs_result['unsynced_detection_pct']:.2f}%")
print(f"  Synchronized detection           : {win_qcs_result['synced_detection_pct']:.2f}%")
print(f"  Detected photons used in BB84     : {win_detected_count}/{num_bits}")
print(f"  Estimated clock offset correction : {win_qcs_result['estimated_offset_ns']:.3f} ns")
print(f"  Estimated clock drift correction  : {win_qcs_result['estimated_drift_ppm']:.3f} ppm")
print()
print("  QCS proof: without clock synchronization, Bob opens the detector")
print("  at the wrong time and loses photons. With QCS, the detector gate")
print("  is recentred before measurement, so more qubits reach BB84.")
print()

# ---- BB84 - Working Table ----

print()
print("  BB84 - Working")
print("  " + "=" * 95)
print()

def get_qubit_state(bit, basis):
    if bit is None or basis is None:
        return "-"
    if basis == '+' and bit == 0: return '|0>'
    if basis == '+' and bit == 1: return '|1>'
    if basis == 'x' and bit == 0: return '|+>'
    if basis == 'x' and bit == 1: return '|->'
    return '?'

COLS = min(6, num_bits)

# Step Header
headers = [f"Photon {i+1}" for i in range(COLS)]
print(f"  {'Step':<20}  " + "  ".join([f"{h:<8}" for h in headers]))
print("  " + "-" * 95)

# Alice's Input Bit
a_bits_str = [str(win_alice_bits[i]) for i in range(COLS)]
lbl = "Alice's Input Bit"
print(f"  {lbl:<20}  " + "  ".join([f"{b:<8}" for b in a_bits_str]))

# Alice's Chosen Basis
a_bases_str = [win_alice_bases[i] for i in range(COLS)]
lbl = "Alice's Chosen Basis"
print(f"  {lbl:<20}  " + "  ".join([f"{b:<8}" for b in a_bases_str]))

# Qubit State Sent
a_states = [get_qubit_state(win_alice_bits[i], win_alice_bases[i]) for i in range(COLS)]
lbl = "Qubit State Sent"
print(f"  {lbl:<20}  " + "  ".join([f"{state:<8}" for state in a_states]))
print("  " + "-" * 95)

if EVE:
    # Eve's Guessed Basis
    eve_bases_str = [win_eve_bases[i] if win_eve_bits[i] is not None else "-" for i in range(COLS)]
    lbl = "Eve's Guessed Basis"
    print(f"  {lbl:<20}  " + "  ".join([f"{b:<8}" for b in eve_bases_str]))
    
    # Eve's Measured Bit
    eve_bits_str = [str(win_eve_bits[i]) if win_eve_bits[i] is not None else "-" for i in range(COLS)]
    lbl = "Eve's Measured Bit"
    print(f"  {lbl:<20}  " + "  ".join([f"{b:<8}" for b in eve_bits_str]))
    
    # Qubit State Resent
    eve_states = [get_qubit_state(win_eve_bits[i], win_eve_bases[i]) if win_eve_bits[i] is not None else "-" for i in range(COLS)]
    lbl = "Qubit State Resent"
    print(f"  {lbl:<20}  " + "  ".join([f"{state:<8}" for state in eve_states]))
    print("  " + "-" * 95)

# Bob's Chosen Basis
b_bases_str = [win_bob_bases[i] for i in range(COLS)]
lbl = "Bob's Chosen Basis"
print(f"  {lbl:<20}  " + "  ".join([f"{b:<8}" for b in b_bases_str]))

# Bob's Measured Bit
b_bits_str = [str(win_bob_bits[i]) for i in range(COLS)]
lbl = "Bob's Measured Bit"
print(f"  {lbl:<20}  " + "  ".join([f"{b:<8}" for b in b_bits_str]))
print("  " + "-" * 95)

# Do Bases Match?
matches = ["YES" if win_alice_bases[i] == win_bob_bases[i] else "NO" for i in range(COLS)]
lbl = "Do Bases Match?"
print(f"  {lbl:<20}  " + "  ".join([f"{m:<8}" for m in matches]))

# Sifting Action
actions = ["KEEP" if m == "YES" else "DISCARD" for m in matches]
lbl = "Sifting Action"
print(f"  {lbl:<20}  " + "  ".join([f"{a:<8}" for a in actions]))
print("  " + "-" * 95)

# Alice's Sifted Key
a_sifted = [str(win_alice_bits[i]) if m == "YES" else "-" for m, i in zip(matches, range(COLS))]
lbl = "Alice's Sifted Key"
print(f"  {lbl:<20}  " + "  ".join([f"{k:<8}" for k in a_sifted]))

# Bob's Sifted Key
b_sifted = [str(win_bob_bits[i]) if m == "YES" else "-" for m, i in zip(matches, range(COLS))]
lbl = "Bob's Sifted Key"
print(f"  {lbl:<20}  " + "  ".join([f"{k:<8}" for k in b_sifted]))

print()
print("          Number of Erroneous Bits")
print("  QBER = --------------------------")
print("             Total Sifted Bits")
print()
print(f"  QBER = {round(win_qber * 100, 2)}%")
print()
if win_qber <= 0.11:
    print(f"  [✓] Key is Accepted as QBER is less than or equal to 11%")
else:
    print(f"  [✗] Key is Aborted as QBER is greater than 11%")
print()



# ---- Step 6: Error Correction ----

print()
print(f"  STEP 6 : Error Correction")
print(f"  {'─' * 50}")
print()
print(f"  Bob's sifted key had {win_errors} bit(s) different from Alice's.")
print(f"  Alice reveals parity information over public channel.")
print(f"  Bob corrects his key to match Alice's.")
print()
print(f"  Before correction  — Bob  : {win_bob_key[:SHOW]}  ...")
print(f"  After  correction  — Bob  : {win_corrected[:SHOW]}  ...")
print(f"  Alice's sifted key        : {win_alice_key[:SHOW]}  ...")
print(f"  Errors fixed: {win_errors}")


# ---- Step 7: Privacy Amplification ----

print()
print(f"  STEP 7 : Privacy Amplification")
print(f"  {'─' * 50}")
print()
print(f"  Even after error correction, Eve may have partial")
print(f"  knowledge of the key (from her intercepted qubits).")
print()
print(f"  Solution: Hash the corrected key using SHA-256.")
print(f"  This compresses it into a shorter key that Eve")
print(f"  provably knows nothing about.")
print()
print(f"  Input  : {len(win_corrected)}-bit corrected sifted key")
print(f"  Method : SHA-256 hash → truncated to {desired_key_length} bits")
print(f"  Output : {desired_key_length}-bit final secret key")
print()
print(f"  Final key (first 32 bits): {win_final_key[:32]}  ...")


# ---- Summary ----

section("KEY ESTABLISHMENT SUMMARY")
print()
print(f"  Attempt succeeded on : Attempt {attempt}")
print(f"  Raw qubits sent      : {num_bits}")
print(f"  Photons detected     : {win_detected_count} ({win_qcs_result['synced_detection_pct']:.2f}%)")
print(f"  Sifted key length    : {len(win_alice_key)} bits")
print(f"  QBER                 : {round(win_qber * 100, 2)} %")
if EVE:
    print(f"  Eve intercepted      : {win_intercepted} qubits ({round(win_intercepted/num_bits*100, 1)}%)")
print(f"  Errors corrected     : {win_errors}")
print(f"  Final key length     : {len(win_final_key)} bits")
print()
print("  ✓  Shared secret key established successfully.")


# =====================================================
# PHASE 2: SECURE MESSAGE TRANSMISSION
# =====================================================

section("PHASE 2 — SECURE MESSAGE TRANSMISSION")

max_chars = desired_key_length // 8
print()
print(f"  Alice can send up to {max_chars} characters")
print(f"  (limited by {desired_key_length}-bit key length in one-time pad)")
print()

alice_message = input("  Alice's secret message: ").strip()

if len(alice_message) > max_chars:
    alice_message = alice_message[:max_chars]
    print(f"  [Message truncated to {max_chars} characters]")


# ---- Step 8: Message to bits ----

section("STEP 8 : Alice converts message to bits")
print()
print(f"  Message  : \"{alice_message}\"")
print()
print(f"  {'Char':>5}  {'ASCII':>5}  {'Binary':>10}  (8 bits per character)")
print(f"  {'────':>5}  {'─────':>5}  {'──────':>10}")

message_bits = []
for char in alice_message:
    val   = ord(char)
    bits  = format(val, '08b')
    bit_list = [int(b) for b in bits]
    message_bits.extend(bit_list)
    print(f"  {repr(char):>5}  {val:>5}  {bits:>10}")

print()
print(f"  Total message bits: {len(message_bits)}")
print(f"  Message bits: {message_bits}")


# ---- Step 9: Encryption ----

section("STEP 9 : Alice encrypts using quantum key (XOR)")
print()
print("  Encryption method: XOR  (One-Time Pad)")
print("  Ciphertext bit = Message bit  XOR  Key bit")
print()
print(f"  {'Char':>5}  {'Msg Bits':>10}  {'Key Bits':>10}  {'Cipher':>10}  XOR explanation")
print(f"  {'────':>5}  {'────────':>10}  {'────────':>10}  {'──────':>10}  ───────────────")

key_index = 0
all_cipher_bits = []

for char in alice_message:
    val      = ord(char)
    msg_bits = [int(b) for b in format(val, '08b')]
    key_bits = win_final_key[key_index: key_index + 8]
    cipher   = [m ^ k for m, k in zip(msg_bits, key_bits)]
    all_cipher_bits.extend(cipher)

    msg_str    = ''.join(str(b) for b in msg_bits)
    key_str    = ''.join(str(b) for b in key_bits)
    cipher_str = ''.join(str(b) for b in cipher)

    print(f"  {repr(char):>5}  {msg_str:>10}  {key_str:>10}  {cipher_str:>10}  "
          f"{msg_str} XOR {key_str} = {cipher_str}")

    key_index += 8

print()
print(f"  Full ciphertext bits: {all_cipher_bits}")
print()
print("  Alice sends this ciphertext over the public channel.")
print("  Eve can intercept it — but without the key, it is")
print("  completely indistinguishable from random noise.")


# ---- Step 10: Decryption ----

section("STEP 10 : Bob decrypts using his copy of the quantum key")
print()
print("  Decryption method: XOR  (same operation — XOR is its own inverse)")
print("  Message bit = Ciphertext bit  XOR  Key bit")
print()
print(f"  {'Cipher':>10}  {'Key Bits':>10}  {'Msg Bits':>10}  {'ASCII':>5}  {'Char':>5}  XOR explanation")
print(f"  {'──────':>10}  {'────────':>10}  {'────────':>10}  {'─────':>5}  {'────':>5}  ───────────────")

key_index       = 0
decrypted_chars = []

for i in range(len(alice_message)):
    cipher_chunk = all_cipher_bits[i * 8: i * 8 + 8]
    key_bits     = win_final_key[key_index: key_index + 8]
    msg_bits     = [c ^ k for c, k in zip(cipher_chunk, key_bits)]

    cipher_str = ''.join(str(b) for b in cipher_chunk)
    key_str    = ''.join(str(b) for b in key_bits)
    msg_str    = ''.join(str(b) for b in msg_bits)

    ascii_val = int(msg_str, 2)
    char      = chr(ascii_val)
    decrypted_chars.append(char)

    print(f"  {cipher_str:>10}  {key_str:>10}  {msg_str:>10}  {ascii_val:>5}  {repr(char):>5}  "
          f"{cipher_str} XOR {key_str} = {msg_str}")

    key_index += 8

decrypted_message = ''.join(decrypted_chars)


# ---- Final result ----

section("RESULT")
print()
print(f"  Alice's original message  : \"{alice_message}\"")
print(f"  Ciphertext sent (bits)    : {all_cipher_bits}")
print(f"  Bob's decrypted message   : \"{decrypted_message}\"")
print()

if decrypted_message == alice_message:
    print("  [✓] SUCCESS: Bob recovered Alice's message perfectly.")
    print()
    print("  The quantum key was used exactly once and then discarded.")
    print("  This is a One-Time Pad — provably unbreakable.")
    if EVE:
        print()
        print("  Even though Eve intercepted some qubits, privacy")
        print("  amplification ensured she gained zero usable key bits.")
else:
    print("  [✗] ERROR: Decrypted message does not match.")

# ---- Optional Graphs ----
print()
print("-" * 55)
gen_graphs = input("  Generate publication-grade research graphs? (y/n): ").strip().lower()
if gen_graphs == 'y':
    from generate_graphs import generate_publication_graphs

    generate_publication_graphs()
