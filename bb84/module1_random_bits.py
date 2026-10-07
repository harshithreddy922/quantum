import secrets


def generate_random_bits(num_bits):
    """
    Generate cryptographically secure random bits.

    Parameters
    ----------
    num_bits : int
        Number of bits to generate.

    Returns
    -------
    list[int]
        List containing random 0s and 1s.
    """

    bits = []

    for _ in range(num_bits):
        bits.append(secrets.randbelow(2))

    return bits


if __name__ == "__main__":

    alice_bits = generate_random_bits(256)

    print("Alice's Secret Bits")
    print(alice_bits)