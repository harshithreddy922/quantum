import random

from qiskit.primitives import StatevectorSampler

from bb84.module2_random_basis import generate_random_bases
from bb84.module3_qubit_preparation import prepare_qubit


def eve_intercept_resend(qubits, interception_rate=0.2):
    """
    Eve's intercept-resend attack.

    Eve does NOT intercept every qubit — she only taps
    a fraction of them (interception_rate). This keeps
    QBER around 10% (below the 11% abort threshold),
    making it realistic: Eve is present but not fully
    caught by a single QBER check.

    interception_rate = 0.2 means Eve intercepts 20%
    of qubits, causing expected QBER of ~10%:
        QBER = interception_rate × 0.5
             = 0.20 × 0.50 = 0.10 (10%)

    Privacy amplification then removes whatever
    partial information Eve collected.
    """

    sampler = StatevectorSampler()

    # Eve randomly chooses a basis for every qubit
    # (she needs a basis ready even if she doesn't intercept)
    eve_bases = generate_random_bases(len(qubits))

    eve_bits = []
    resent_qubits = []

    for circuit, basis in zip(qubits, eve_bases):

        # Eve flips a coin — does she intercept this qubit?
        if random.random() > interception_rate:

            # Eve lets this qubit pass through untouched
            resent_qubits.append(circuit)
            eve_bits.append(None)

        else:

            # Eve intercepts this qubit
            working_circuit = circuit.copy()

            # If Eve chooses diagonal basis,
            # rotate before measuring
            if basis == 'x':
                working_circuit.h(0)

            # Eve measures
            working_circuit.measure(0, 0)

            job = sampler.run([working_circuit], shots=1)
            result = job.result()

            counts = result[0].data.c.get_counts()

            eve_bit = int(list(counts.keys())[0])

            eve_bits.append(eve_bit)

            # Eve creates a new qubit and sends it to Bob
            new_qubit = prepare_qubit(eve_bit, basis)

            resent_qubits.append(new_qubit)

    intercepted = sum(1 for b in eve_bits if b is not None)

    return resent_qubits, eve_bases, eve_bits, intercepted