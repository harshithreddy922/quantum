def text_to_bits(text):
    """
    Convert a string to a list of bits.
    Each character becomes 8 bits (ASCII).
    """

    bits = []

    for char in text:

        ascii_val = ord(char)

        char_bits = []

        for _ in range(8):
            char_bits.append(ascii_val & 1)
            ascii_val >>= 1

        # Least significant bit first
        char_bits.reverse()

        bits.extend(char_bits)

    return bits


def bits_to_text(bits):
    """
    Convert a list of bits back to a string.
    Every 8 bits form one character.
    """

    text = ""

    for i in range(0, len(bits), 8):

        byte = bits[i:i + 8]

        if len(byte) < 8:
            break

        ascii_val = 0

        for bit in byte:
            ascii_val = (ascii_val << 1) | bit

        text += chr(ascii_val)

    return text


def encrypt(message, key_bits):
    """
    Encrypt a message using XOR with the quantum key.

    This is a One-Time Pad — the most secure form
    of encryption. Each message bit is XOR'd with
    the corresponding key bit.

    The message is truncated or padded to fit
    within the available key length.

    Parameters
    ----------
    message  : str   — plaintext message from Alice
    key_bits : list  — quantum key bits

    Returns
    -------
    ciphertext_bits : list of encrypted bits
    message_used    : str — actual message sent (may be truncated)
    """

    max_chars = len(key_bits) // 8

    # Truncate message if it's longer than the key allows
    if len(message) > max_chars:
        message = message[:max_chars]
        print(f"    [Note] Message truncated to {max_chars} characters")

    message_bits = text_to_bits(message)

    # XOR each message bit with corresponding key bit
    ciphertext_bits = []

    for msg_bit, key_bit in zip(message_bits, key_bits):

        ciphertext_bits.append(msg_bit ^ key_bit)

    return ciphertext_bits, message


def decrypt(ciphertext_bits, key_bits):
    """
    Decrypt ciphertext using XOR with the quantum key.

    XOR is its own inverse:
        encrypt: C = M XOR K
        decrypt: M = C XOR K

    Parameters
    ----------
    ciphertext_bits : list — received encrypted bits
    key_bits        : list — quantum key bits

    Returns
    -------
    decrypted_text : str — recovered plaintext
    """

    decrypted_bits = []

    for cipher_bit, key_bit in zip(ciphertext_bits, key_bits):

        decrypted_bits.append(cipher_bit ^ key_bit)

    return bits_to_text(decrypted_bits)
