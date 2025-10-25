import numpy as np
from math import log10, sqrt

Kw = 1e-14

# --- Functions for each titration type ---

def pH_strong_acid_titration(Ca=0.100, V0=25.0, Cb=0.100, Vmax=50.0, step=1.0):
    Vs = np.arange(0, Vmax+step, step)
    rows = []
    n_acid = Ca * V0 / 1000.0
    for V in Vs:
        n_base = Cb * V / 1000.0
        Vtot = (V0 + V)/1000.0
        if n_base < n_acid:
            H = (n_acid - n_base) / Vtot
            pH = -log10(H)
        elif abs(n_base - n_acid) < 1e-12:
            pH = 7.00
        else:
            OH = (n_base - n_acid) / Vtot
            pOH = -log10(OH)
            pH = 14.0 - pOH
        rows.append((V, pH))
    return rows

def pH_strong_base_titration(Cb=0.100, V0=25.0, Ca=0.100, Vmax=50.0, step=1.0):
    Vs = np.arange(0, Vmax+step, step)
    rows = []
    n_base = Cb * V0 / 1000.0
    for V in Vs:
        n_acid = Ca * V / 1000.0
        Vtot = (V0 + V)/1000.0
        if n_acid < n_base:
            OH = (n_base - n_acid) / Vtot
            pOH = -log10(OH)
            pH = 14.0 - pOH
        elif abs(n_acid - n_base) < 1e-12:
            pH = 7.00
        else:
            H = (n_acid - n_base) / Vtot
            pH = -log10(H)
        rows.append((V, pH))
    return rows

def pH_weak_acid_titration(Ca=0.100, V0=25.0, Cb=0.100, pKa=4.76, Vmax=50.0, step=1.0):
    Vs = np.arange(0, Vmax+step, step)
    Ka = 10**(-pKa)
    rows = []
    n_HA_init = Ca * V0 / 1000.0
    for V in Vs:
        n_OH = Cb * V / 1000.0
        Vtot = (V0 + V)/1000.0
        if n_OH == 0:
            C = n_HA_init / Vtot
            a=1.0; b=Ka; c=-Ka*C
            x = (-b + sqrt(b*b - 4*a*c))/(2*a)
            H = x
            pH = -log10(H)
        elif n_OH < n_HA_init - 1e-12:
            n_A = n_OH
            n_HA = n_HA_init - n_OH
            pH = pKa + log10(n_A / n_HA)
        elif abs(n_OH - n_HA_init) < 1e-12:
            C_salt = n_OH / Vtot
            Kb = Kw / Ka
            OH = sqrt(Kb * C_salt)
            pOH = -log10(OH)
            pH = 14.0 - pOH
        else:
            OH = (n_OH - n_HA_init) / Vtot
            pOH = -log10(OH)
            pH = 14.0 - pOH
        rows.append((V, pH))
    return rows

def pH_weak_base_titration(Cb=0.100, V0=25.0, Ca=0.100, pKb=4.75, Vmax=50.0, step=1.0):
    Vs = np.arange(0, Vmax+step, step)
    Kb = 10**(-pKb)
    pKa = 14.0 - pKb
    rows = []
    n_B_init = Cb * V0 / 1000.0
    for V in Vs:
        n_H = Ca * V / 1000.0
        Vtot = (V0 + V)/1000.0
        if n_H == 0:
            C = n_B_init / Vtot
            a=1.0; b=Kb; c=-Kb*C
            x = (-b + sqrt(b*b - 4*a*c))/(2*a)
            OH = x
            pOH = -log10(OH)
            pH = 14.0 - pOH
        elif n_H < n_B_init - 1e-12:
            n_B = n_B_init - n_H
            n_BH = n_H
            pH = pKa + log10(n_B / n_BH)
        elif abs(n_H - n_B_init) < 1e-12:
            C_salt = n_H / Vtot
            Ka = Kw / Kb
            H = sqrt(Ka * C_salt)
            pH = -log10(H)
        else:
            H = (n_H - n_B_init) / Vtot
            pH = -log10(H)
        rows.append((V, pH))
    return rows

def pH_diprotic_acid_titration(Ca=0.050, V0=25.0, Cb=0.100, pKa1=2.00, pKa2=7.00, Vmax=50.0, step=0.5):
    Ka1 = 10**(-pKa1)
    Ka2 = 10**(-pKa2)
    Vs = np.arange(0, Vmax+step, step)
    rows = []
    n_H2A = Ca * V0 / 1000.0
    for V in Vs:
        n_OH = Cb * V / 1000.0
        Vtot = (V0 + V)/1000.0
        if n_OH == 0:
            C = n_H2A / Vtot
            a=1.0; b=Ka1; c=-Ka1*C
            x = (-b + sqrt(b*b - 4*a*c))/(2*a)
            H = x
            pH = -log10(H)
        elif n_OH < n_H2A - 1e-12:
            n_HA = n_OH
            n_H2A_rem = n_H2A - n_OH
            pH = pKa1 + log10(n_HA / n_H2A_rem)
        elif abs(n_OH - n_H2A) < 1e-12:
            pH = 0.5 * (pKa1 + pKa2)
        elif n_OH < 2*n_H2A - 1e-12:
            n_A2 = n_OH - n_H2A
            n_HA = n_H2A - (n_OH - n_H2A)
            pH = pKa2 + log10(n_A2 / n_HA)
        elif abs(n_OH - 2*n_H2A) < 1e-12:
            C_salt = n_OH / Vtot
            Kb2 = Kw / Ka2
            OH = sqrt(Kb2 * C_salt)
            pOH = -log10(OH)
            pH = 14.0 - pOH
        else:
            OH = (n_OH - 2*n_H2A) / Vtot
            pOH = -log10(OH)
            pH = 14.0 - pOH
        rows.append((V, pH))
    return rows


if __name__ == "__main__":
    all_cases = {
        "strong_acid.txt": pH_strong_acid_titration,
        "strong_base.txt": pH_strong_base_titration,
        "weak_acid.txt": pH_weak_acid_titration,
        "weak_base.txt": pH_weak_base_titration,
        "diprotic.txt": pH_diprotic_acid_titration,
    }

    for filename, func in all_cases.items():
        data = func()
        with open(filename, "w") as f:
            for V, pH in data:
                f.write(f"{V:.2f} {pH:.4f}\n")
        print(f"Wrote {filename}")
