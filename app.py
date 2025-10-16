import streamlit as st
import numpy as np
from scipy.optimize import linprog

st.set_page_config(page_title="AgriLign — Crop Mix Optimizer", page_icon="🌾", layout="centered")

st.title("🌾 AgriLign — Crop Mix Optimizer (Corn vs Soy)")
st.caption("Linear program solved with SciPy (no external solvers).")

with st.expander("Model", expanded=False):
    st.markdown(
        """
**Decision variables**: Corn acres (C), Soy acres (S)

**Objective**: Maximize profit = `p_c*C + p_s*S`

**Constraints**:
- Land: `C + S = Total` (or `≤ Total` if idle allowed)
- Labor: `a_c*C + a_s*S ≤ cap`
- Herbicide budget: `h_c*C + h_s*S ≤ cap`
- Nitrogen: `n_c*C + n_s*S ≤ cap`
- **Efficacy (linear)**: `e_c*C + e_s*S ≥ target*(C+S)` → rearranged to ` (e_c-target)*C + (e_s-target)*S ≥ 0`
        """
    )

# ---------- Sidebar inputs ----------
st.sidebar.header("Inputs")

total_acres = st.sidebar.number_input("Total acres", min_value=0.0, value=1000.0, step=10.0)

profit_corn = st.sidebar.number_input("Profit/acre — Corn ($)", value=350.0, step=10.0)
profit_soy  = st.sidebar.number_input("Profit/acre — Soy ($)",  value=200.0, step=10.0)

labor_corn  = st.sidebar.number_input("Labor hr/acre — Corn", min_value=0.0, value=0.75, step=0.05)
labor_soy   = st.sidebar.number_input("Labor hr/acre — Soy",  min_value=0.0, value=0.85, step=0.05)

herb_corn   = st.sidebar.number_input("Herbicide $/acre — Corn", min_value=0.0, value=30.0, step=1.0)
herb_soy    = st.sidebar.number_input("Herbicide $/acre — Soy",  min_value=0.0, value=20.0, step=1.0)

N_corn      = st.sidebar.number_input("Nitrogen lb/acre — Corn", min_value=0.0, value=10.0, step=1.0)
N_soy       = st.sidebar.number_input("Nitrogen lb/acre — Soy",  min_value=0.0, value=20.0, step=1.0)

labor_cap   = st.sidebar.number_input("Labor cap (hr)", min_value=0.0, value=2000.0, step=10.0)
herb_cap    = st.sidebar.number_input("Herbicide budget ($)", min_value=0.0, value=30000.0, step=100.0)
N_cap       = st.sidebar.number_input("Nitrogen cap (lb)", min_value=0.0, value=90000.0, step=100.0)

eff_corn    = st.sidebar.number_input("Efficacy — Corn", min_value=0.0, max_value=1.0, value=0.90, step=0.01, format="%.2f")
eff_soy     = st.sidebar.number_input("Efficacy — Soy",  min_value=0.0, max_value=1.0, value=0.87, step=0.01, format="%.2f")
target      = st.sidebar.number_input("Minimum efficacy target", min_value=0.0, max_value=1.0, value=0.88, step=0.01, format="%.2f")

idle_ok     = st.sidebar.checkbox("Allow idle land (≤ total acres)", value=False)

# ---------- Build LP for SciPy ----------
# Maximize p·x  <=>  Minimize -p·x
c = np.array([-profit_corn, -profit_soy])  # objective coefficients (negated)

A_ub = []
b_ub = []

# Resource caps: a_c*C + a_s*S ≤ cap
A_ub.append([labor_corn, labor_soy]);   b_ub.append(labor_cap)
A_ub.append([herb_corn,  herb_soy]);    b_ub.append(herb_cap)
A_ub.append([N_corn,     N_soy]);       b_ub.append(N_cap)

# Linear efficacy: (e_c - target)*C + (e_s - target)*S ≥ 0  -> multiply by -1 to fit ≤
A_ub.append([-(eff_corn - target), -(eff_soy - target)]); b_ub.append(0.0)

A_ub = np.array(A_ub)
b_ub = np.array(b_ub)

A_eq = None
b_eq = None
if idle_ok:
    # C + S ≤ total_acres
    A_ub = np.vstack([A_ub, [1.0, 1.0]])
    b_ub = np.append(b_ub, total_acres)
else:
    # C + S = total_acres
    A_eq = np.array([[1.0, 1.0]])
    b_eq = np.array([total_acres])

bounds = [(0, None), (0, None)]  # C ≥ 0, S ≥ 0

# ---------- Solve ----------
if st.button("🔎 Solve", type="primary"):
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")

    if not res.success:
        st.error(f"Solver failed: {res.message}")
        st.info("Try: allow idle land, lower the efficacy target, or relax a cap.")
    else:
        C, S = res.x
        total_profit = -res.fun  # we minimized -profit

        labor_used = labor_corn*C + labor_soy*S
        herb_used  = herb_corn*C  + herb_soy*S
        N_used     = N_corn*C     + N_soy*S
        eff_LHS    = eff_corn*C + eff_soy*S
        eff_RHS    = target*(C+S)

        c1, c2, c3 = st.columns(3)
        c1.metric("Corn acres", f"{C:.2f}")
        c2.metric("Soy acres",  f"{S:.2f}")
        c3.metric("Max profit", f"${total_profit:,.2f}")

        st.markdown("#### Constraint usage")
        st.table({
            "Constraint": ["Land", "Labor", "Herbicide", "Nitrogen", "Efficacy LHS", "Efficacy RHS"],
            "Used": [f"{(C+S):.2f}", f"{labor_used:.2f}", f"{herb_used:.2f}", f"{N_used:.2f}", f"{eff_LHS:.2f}", f"{eff_RHS:.2f}"],
            "Cap / Target": [f"{total_acres:.2f}", f"{labor_cap:.2f}", f"{herb_cap:.2f}", f"{N_cap:.2f}", "—", "—"]
        })
else:
    st.info("Set inputs in the sidebar, then click **Solve**.")
