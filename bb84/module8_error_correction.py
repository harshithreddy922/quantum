def error_correction(alice_key, bob_key):

    if len(alice_key) != len(bob_key):
        raise ValueError("Keys must have the same length.")

    corrected_key = bob_key.copy()

    errors = 0

    for i in range(len(alice_key)):

        if alice_key[i] != corrected_key[i]:

            corrected_key[i] = alice_key[i]
            errors += 1

    return corrected_key, errors