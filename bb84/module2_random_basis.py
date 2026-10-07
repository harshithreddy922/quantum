import secrets

def generate_random_bases(num_bits):
    """
    Generate random BB84 bases.

    Returns:
        List containing '+' or 'x'
    """

    bases = []

    for _ in range(num_bits):

        if secrets.randbelow(2) == 0:
            bases.append('+')
        else:
            bases.append('x')

    return bases


if __name__ == "__main__":

    alice_bases = generate_random_bases(10)

    print("Alice's Bases:")
    print(alice_bases)