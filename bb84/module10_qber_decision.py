def qber_decision(qber, threshold=0.11):

    if qber <= threshold:
        return True

    return False