import random

def transmit(qubits, noise_rate=0.03):
    """
    Realistic quantum channel.

    Simulates environmental noise (decoherence, thermal fluctuations,
    and detector dark counts) by randomly applying Pauli errors 
    (X, Y, or Z gates) to the passing qubits.

    Parameters
    ----------
    qubits     : list of QuantumCircuit
    noise_rate : float (0.0 to 1.0)
                 Probability that a qubit experiences a random error.
                 Default is 0.03 (3% natural channel noise).
    """
    noisy_qubits = []

    for circuit in qubits:
        
        # We create a copy so the simulation doesn't accidentally
        # change Alice's original prepared qubits.
        working_circuit = circuit.copy()

        # Is this qubit affected by noise?
        if random.random() < noise_rate:
            
            # Apply a random quantum error
            # X = bit flip, Z = phase flip, Y = both
            error_type = random.choice(['x', 'y', 'z'])
            
            if error_type == 'x':
                working_circuit.x(0)
            elif error_type == 'y':
                working_circuit.y(0)
            elif error_type == 'z':
                working_circuit.z(0)

        noisy_qubits.append(working_circuit)

    return noisy_qubits