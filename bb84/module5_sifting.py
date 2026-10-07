def sift_key(alice_bits, alice_bases, bob_bases, bob_bits):

    alice_key = []
    bob_key = []

    for alice_bit, alice_basis, bob_basis, bob_bit in zip(
        alice_bits,
        alice_bases,
        bob_bases,
        bob_bits
    ):

        # Keep only positions where both used the same basis
        if alice_basis == bob_basis:
            alice_key.append(alice_bit)
            bob_key.append(bob_bit)

    return alice_key, bob_key