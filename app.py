import streamlit as st
from ortools.linear_solver import pywraplp

st.set_page_config(page_title="CropMix Optimizer", page_icon="🌾", layout="centered")

st.title("🌾 CropMix Optimizer — Online")
st.caption("Linear program with efficacy constraint. Runs on free hosts (Streamlit Cloud / Render) without external solvers.")

with st.expander("Model", expanded=False):
    st.markdown(
        """
        Decision variables: **Corn acres (C)** and **Soy acres (S)**.  
        Objective: Maximize `profit_corn*C + profit_soy*S`.  
        Constraints: land, labor, herbicide $, nitrogen, and **linear efficacy** `eff_corn*C + eff_soy*S ≥ target*(C+S)`.
        """
    )

# ---------- Inputs ----------
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

target      = st.sidebar.number_input("Minimum efficacy target", min_value=0.0, max_value=1.0, value=0.88, step=0.01, format="%.2f")
idle_ok     = st.sidebar.checkbox("Allow idle land (≤ total acres)", value=False)

def solve():
    # Use OR-Tools GLOP (LP) for maximum cloud compatibility
    solver = pywraplp.Solver.CreateSolver("GLOP")
    if solver is None:
        return {"status": "ERROR", "msg": "Could not create OR-Tools solver."}

    C = solver.NumVar(0.0, solver.infinity(), "Corn")
    S = solver.NumVar(0.0, solver.infinity(), "Soy")

    # Objective
    solver.Maximize(profit_corn*C + profit_soy*S)

    # Constraints
    if idle_ok:
        solver.Add(C + S <= total_acres)
    else:
        solver.Add(C + S == total_acres)

    solver.Add(labor_corn*C + labor_soy*S <= labor_cap)
    solver.Add(herb_corn*C  + herb_soy*S  <= herb_cap)
    solver.Add(N_corn*C     + N_soy*S     <= N_cap)
    solver.Add((0.0 + 1.0*0)*C >= 0)  # no-op to ensure variables used

    # Linear efficacy: eff_corn*C + eff_soy*S >= target*(C + S)
    solver.Add((st.session_state.get("eff_corn", 0.90) if True else 0.90)*C + 
               (st.session_state.get("eff_soy", 0.87) if True else 0.87)*S >= target*(C + S))

    status = solver.Solve()
    if status != pywraplp.Solver.OPTIMAL:
        return {"status": "INFEASIBLE_OR_ERROR", "msg": "No optimal solution. Try relaxing caps, lowering target, or allowing idle land."}

    Cval = C.solution_value()
    Sval = S.solution_value()
    profit = solver.Objective().Value()
    used = {
        "Land": Cval + Sval,
        "Labor": labor_corn*Cval + labor_soy*Sval,
        "Herbicide": herb_corn*Cval + herb_soy*Sval,
        "Nitrogen": N_corn*Cval + N_soy*Sval,
        "Efficacy_LHS": (st.session_state.get("eff_corn", 0.90))*Cval + (st.session_state.get("eff_soy", 0.87))*Sval,
        "Efficacy_RHS": target*(Cval + Sval),
    }
    return {"status": "OPTIMAL", "corn": Cval, "soy": Sval, "profit": profit, "used": used}

st.session_state.setdefault("eff_corn", 0.90)
st.session_state.setdefault("eff_soy", 0.87)

with st.form("solveform"):
    col1, col2 = st.columns(2)
    with col1:
        st.number_input("Efficacy — Corn", min_value=0.0, max_value=1.0, value=st.session_state["eff_corn"], step=0.01, format="%.2f", key="eff_corn")
    with col2:
        st.number_input("Efficacy — Soy", min_value=0.0, max_value=1.0, value=st.session_state["eff_soy"], step=0.01, format="%.2f", key="eff_soy")
    submitted = st.form_submit_button("🔎 Solve")

if submitted:
    out = solve()
    if out["status"] != "OPTIMAL":
        st.error(out.get("msg", "Solve failed."))
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Corn acres", f"{out['corn']:.2f}")
        c2.metric("Soy acres", f"{out['soy']:.2f}")
        c3.metric("Max profit", f"${out['profit']:,.2f}")

        st.markdown("#### Constraint usage")
        st.table({
            "Constraint": ["Land", "Labor", "Herbicide", "Nitrogen", "Efficacy LHS", "Efficacy RHS"],
            "Used": [f"{out['used']['Land']:.2f}",
                     f"{out['used']['Labor']:.2f}",
                     f"{out['used']['Herbicide']:.2f}",
                     f"{out['used']['Nitrogen']:.2f}",
                     f"{out['used']['Efficacy_LHS']:.2f}",
                     f"{out['used']['Efficacy_RHS']:.2f}"]
        })
