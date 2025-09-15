# Creating titration datasets for five cases and displaying them as DataFrames.
# The DataFrames will include: V_added (mL), pH, total_volume (mL), notes
# Cases:
# 1) Strong acid (HCl) titrated by strong base (NaOH)
# 2) Strong base (NaOH) titrated by strong acid (HCl)
# 3) Weak acid (acetic acid, pKa=4.76) titrated by strong base (NaOH)
# 4) Weak base (ammonia, pKb=4.75 -> pKa(conj)=9.25) titrated by strong acid (HCl)
# 5) Diprotic acid (H2A) titrated by strong base (NaOH), pKa1=2.00, pKa2=7.00
#
# Display the results as interactive tables for the user.
import numpy as np
import pandas as pd
from math import log10, sqrt

Kw = 1e-14

def pH_strong_acid_titration(Ca=0.100, V0=25.0, Cb=0.100, Vmax=50.0, step=1.0):
    Vs = np.arange(0, Vmax+step, step)
    rows = []
    n_acid = Ca * V0 / 1000.0  # mol
    for V in Vs:
        n_base = Cb * V / 1000.0
        Vtot = (V0 + V)/1000.0
        if n_base < n_acid:
            # excess H+
            H = (n_acid - n_base) / Vtot
            pH = -log10(H)
            note = "excess H+"
        elif abs(n_base - n_acid) < 1e-12:
            pH = 7.00
            note = "equivalence (neutral)"
        else:
            OH = (n_base - n_acid) / Vtot
            pOH = -log10(OH)
            pH = 14.0 - pOH
            note = "excess OH-"
        rows.append([round(V,3), round(pH,4), round(Vtot*1000,3), note])
    df = pd.DataFrame(rows, columns=["V_added_mL","pH","total_volume_mL","note"])
    return df

def pH_strong_base_titration(Cb=0.100, V0=25.0, Ca=0.100, Vmax=50.0, step=1.0):
    # symmetric: titrating strong base with strong acid
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
            note = "excess OH-"
        elif abs(n_acid - n_base) < 1e-12:
            pH = 7.00
            note = "equivalence (neutral)"
        else:
            H = (n_acid - n_base) / Vtot
            pH = -log10(H)
            note = "excess H+"
        rows.append([round(V,3), round(pH,4), round(Vtot*1000,3), note])
    df = pd.DataFrame(rows, columns=["V_added_mL","pH","total_volume_mL","note"])
    return df

def pH_weak_acid_titration(Ca=0.100, V0=25.0, Cb=0.100, pKa=4.76, Vmax=50.0, step=1.0):
    Vs = np.arange(0, Vmax+step, step)
    Ka = 10**(-pKa)
    rows = []
    n_HA_init = Ca * V0 / 1000.0
    for V in Vs:
        n_OH = Cb * V / 1000.0
        Vtot = (V0 + V)/1000.0
        if n_OH == 0:
            # initial weak acid pH: solve HA <-> H+ + A-
            C = n_HA_init / Vtot
            # Solve x^2/(C - x) = Ka -> x^2 + Ka*x - Ka*C =0
            a=1.0; b=Ka; c=-Ka*C
            x = (-b + sqrt(b*b - 4*a*c))/(2*a)
            H = x
            pH = -log10(H)
            note = "initial weak acid"
        elif n_OH < n_HA_init - 1e-12:
            # buffer region: use Henderson-Hasselbalch with amounts
            n_A = n_OH
            n_HA = n_HA_init - n_OH
            ratio = (n_A / n_HA) if n_HA>0 else 1e12
            pH = pKa + log10(ratio)
            note = "buffer region"
        elif abs(n_OH - n_HA_init) < 1e-12:
            # equivalence: solution of A- (salt) hydrolysis
            C_salt = n_OH / Vtot
            Kb = Kw / Ka
            OH = sqrt(Kb * C_salt)
            pOH = -log10(OH)
            pH = 14.0 - pOH
            note = "equivalence (conjugate base hydrolysis)"
        else:
            # excess OH
            OH = (n_OH - n_HA_init) / Vtot
            pOH = -log10(OH)
            pH = 14.0 - pOH
            note = "excess OH-"
        rows.append([round(V,3), round(pH,4), round(Vtot*1000,3), note])
    df = pd.DataFrame(rows, columns=["V_added_mL","pH","total_volume_mL","note"])
    return df

def pH_weak_base_titration(Cb=0.100, V0=25.0, Ca=0.100, pKb=4.75, Vmax=50.0, step=1.0):
    Vs = np.arange(0, Vmax+step, step)
    Kb = 10**(-pKb)
    pKa = 14.0 - pKb  # pKa of conjugate acid
    rows = []
    n_B_init = Cb * V0 / 1000.0
    for V in Vs:
        n_H = Ca * V / 1000.0
        Vtot = (V0 + V)/1000.0
        if n_H == 0:
            # initial weak base pH: solve B + H2O <-> BH+ + OH-
            C = n_B_init / Vtot
            # x^2/(C - x) = Kb -> x^2 + Kb*x - Kb*C =0
            a=1.0; b=Kb; c=-Kb*C
            x = (-b + sqrt(b*b - 4*a*c))/(2*a)
            OH = x
            pOH = -log10(OH)
            pH = 14.0 - pOH
            note = "initial weak base"
        elif n_H < n_B_init - 1e-12:
            # buffer region of base/acid (BH+ / B): use Henderson for conjugate acid
            n_B = n_B_init - n_H
            n_BH = n_H
            # pH = pKa + log([base]/[acid]) where pKa is conjugate acid
            ratio = (n_B / n_BH) if n_BH>0 else 1e12
            pH = pKa + log10(ratio)
            note = "buffer region"
        elif abs(n_H - n_B_init) < 1e-12:
            # equivalence: solution contains BH+ (acid) -> pH from Ka of BH+
            C_salt = n_H / Vtot
            Ka = Kw / Kb
            H = sqrt(Ka * C_salt)
            pH = -log10(H)
            note = "equivalence (conjugate acid hydrolysis)"
        else:
            # excess H+
            H = (n_H - n_B_init) / Vtot
            pH = -log10(H)
            note = "excess H+"
        rows.append([round(V,3), round(pH,4), round(Vtot*1000,3), note])
    df = pd.DataFrame(rows, columns=["V_added_mL","pH","total_volume_mL","note"])
    return df

def pH_diprotic_acid_titration(Ca=0.050, V0=25.0, Cb=0.100, pKa1=2.00, pKa2=7.00, Vmax=50.0, step=0.5):
    # Approximate piecewise method using HH where appropriate and known relations for amphiprotic points.
    Ka1 = 10**(-pKa1)
    Ka2 = 10**(-pKa2)
    Vs = np.arange(0, Vmax+step, step)
    rows = []
    n_H2A = Ca * V0 / 1000.0
    V1 = (n_H2A * 1.0) / Cb * 1000.0  # mL for first eq (1 mol OH per mol H2A)
    V2 = (n_H2A * 2.0) / Cb * 1000.0  # mL for second eq
    for V in Vs:
        n_OH = Cb * V / 1000.0
        Vtot = (V0 + V)/1000.0
        if n_OH == 0:
            # initial H2A: solve first dissociation approximately
            C = n_H2A / Vtot
            a=1.0; b=Ka1; c=-Ka1*C
            x = (-b + sqrt(b*b - 4*a*c))/(2*a)
            H = x
            pH = -log10(H)
            note = "initial diprotic acid"
        elif n_OH < n_H2A - 1e-12:
            # before first eq: use HH for first dissociation (H2A <-> H+ + HA-)
            n_HA = n_OH
            n_H2A_rem = n_H2A - n_OH
            ratio = (n_HA / n_H2A_rem) if n_H2A_rem>0 else 1e12
            pH = pKa1 + log10(ratio)
            note = "between 0 and first eq (buffer of H2A/HA-)"
        elif abs(n_OH - n_H2A) < 1e-12:
            # first equivalence: amphiprotic HA- dominates; pH ~ 1/2(pKa1+pKa2)
            pH = 0.5*(pKa1 + pKa2)
            note = "first equivalence (amphiprotic HA-)"
        elif n_OH < 2*n_H2A - 1e-12:
            # between first and second eq: HA- partially neutralized to A2-
            n_A2 = n_OH - n_H2A
            n_HA = n_H2A - (n_OH - n_H2A) if n_OH>n_H2A else 0.0
            # Use HH for second dissociation HA- <-> H+ + A2-: pH = pKa2 + log([A2-]/[HA-])
            if n_HA <= 0:
                pH = pKa2
            else:
                ratio = (n_A2 / n_HA) if n_HA>0 else 1e12
                pH = pKa2 + log10(ratio)
            note = "between first and second eq (buffer of HA-/A2-)"
        elif abs(n_OH - 2*n_H2A) < 1e-12:
            # second equivalence: solution contains A2- only, hydrolysis of A2- negligible if pKa2 small; compute from Kb2
            C_salt = n_OH / Vtot
            # approximate OH from hydrolysis of A2- (very weak): Kb2 ~ Kw/Ka2
            Kb2 = Kw / Ka2
            OH = sqrt(Kb2 * C_salt)
            pOH = -log10(OH) if OH>0 else 7.0
            pH = 14.0 - pOH
            note = "second equivalence (A2- solution)"
        else:
            # excess OH after second eq
            OH = (n_OH - 2*n_H2A) / Vtot
            pOH = -log10(OH)
            pH = 14.0 - pOH
            note = "excess OH- after second eq"
        rows.append([round(V,3), round(pH,4), round(Vtot*1000,3), note])
    df = pd.DataFrame(rows, columns=["V_added_mL","pH","total_volume_mL","note"])
    # add metadata as attributes for clarity
    df.attrs = {"V1_mL": round(V1,4), "V2_mL": round(V2,4), "pKa1": pKa1, "pKa2": pKa2}
    return df

# Generate datasets
df1 = pH_strong_acid_titration()
df2 = pH_strong_base_titration()
df3 = pH_weak_acid_titration()
df4 = pH_weak_base_titration()
df5 = pH_diprotic_acid_titration()

# Also save CSVs for download
df1.to_csv("1_strong_acid_vs_strong_base.csv", index=False)
df2.to_csv("2_strong_base_vs_strong_acid.csv", index=False)
df3.to_csv("3_weak_acid_vs_strong_base.csv", index=False)
df4.to_csv("4_weak_base_vs_strong_acid.csv", index=False)
df5.to_csv("5_diprotic_acid_vs_strong_base.csv", index=False)

"1_strong_acid_vs_strong_base.csv", "2_strong_base_vs_strong_acid.csv", \
"3_weak_acid_vs_strong_base.csv", "4_weak_base_vs_strong_acid.csv", \
"5_diprotic_acid_vs_strong_base.csv"

