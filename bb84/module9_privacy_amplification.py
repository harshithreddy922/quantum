import hashlib


def privacy_amplification(key, output_length=None):

    # Convert the key from list of integers to a string
    key_string = ''.join(str(bit) for bit in key)

    # Hash the key using SHA-256
    hash_value = hashlib.sha256(
        key_string.encode()
    ).digest()

    # Convert bytes to binary string
    binary_key = ''.join(
        format(byte, '08b')
        for byte in hash_value
    )

    # If no output length is specified,
    # return the complete 256-bit hash
    if output_length is None:
        output_length = 256

    # Don't request more bits than the hash provides
    output_length = min(output_length, 256)

    return [
        int(bit)
        for bit in binary_key[:output_length]
    ]