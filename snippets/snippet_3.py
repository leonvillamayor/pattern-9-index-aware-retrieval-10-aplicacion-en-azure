# job_ece.py — ejecutado en compute cluster (Standard_DS3_v2 basta)
import numpy as np
from sklearn.metrics import accuracy_score

def expected_calibration_error(y_true, y_prob, n_bins=10):
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    for lo, hi in zip(bins[:-1], bins[1:]):
        mask = (y_prob > lo) & (y_prob <= hi)
        if mask.sum() == 0:
            continue
        acc_bin  = accuracy_score(y_true[mask], (y_prob[mask] > 0.5).astype(int))
        conf_bin = y_prob[mask].mean()
        ece += (mask.sum() / len(y_true)) * abs(acc_bin - conf_bin)
    return ece