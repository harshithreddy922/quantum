def calculate_qber(alice_key, bob_key):

    if len(alice_key) != len(bob_key):
        raise ValueError("Alice and Bob keys must have the same length.")

    if len(alice_key) == 0:
        return 0.0

    errors = 0

    for alice_bit, bob_bit in zip(alice_key, bob_key):

        if alice_bit != bob_bit:
            errors += 1

    qber = errors / len(alice_key)

    return qber