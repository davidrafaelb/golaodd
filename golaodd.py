import math
import pandas as pd
import streamlit as st

# --------------------------
# Funciones Poisson
# --------------------------
def poisson_pmf(k, mu):
    return math.exp(-mu) * (mu ** k) / math.factorial(k)

def poisson_cdf(k, mu):
    return sum(poisson_pmf(i, mu) for i in range(k+1)) if k >= 0 else 0.0

def poisson_sf(k, mu):
    if k <= 0:
        return 1.0
    return 1.0 - poisson_cdf(k-1, mu)

def ou_table(lam_total, minute_now, goals_so_far, match_duration_probs, max_line_half=8):
    rate_per_min = lam_total / match_duration_probs
    remaining = max(0.0, match_duration_probs - minute_now)
    mu_remaining = rate_per_min * remaining

    rows = []
    for half in range(0, max_line_half+1):
        line = half + 0.5
        x = half
        y_max = x - goals_so_far
        under_prob = poisson_cdf(y_max, mu_remaining) if y_max >= 0 else 0.0
        over_prob = 1 - under_prob
        rows.append({
            "Línea": f"{line:.1f}",
            "Prob Under": round(under_prob, 4),
            "Odds Under": round(1/under_prob, 2) if under_prob > 0 else float("inf"),
            "Prob Over": round(over_prob, 4),
            "Odds Over": round(1/over_prob, 2) if over_prob > 0 else float("inf")
        })
    return pd.DataFrame(rows)

def next_goals(lam_total, minute_now, match_duration_probs, extra_minutes, k_max=5, acceleration_factor=0.0):
    rate_per_min = lam_total / match_duration_probs
    remaining = max(0.0, match_duration_probs - minute_now)
    mu_remaining = rate_per_min * remaining

    rows = []
    for k in range(1, k_max+1):
        expected_wait_k = k / rate_per_min
        expected_minute_k = minute_now + expected_wait_k

        # --- APLICAR ACELERACIÓN SOLO SI EL GOL ESTÁ EN EL 2T ---
        if expected_minute_k >= 45 and acceleration_factor > 0:
            acceleration_percentage = acceleration_factor / 100.0
            expected_minute_k = 45 + (expected_minute_k - 45) * (1 - acceleration_percentage)

        # ⚠️ Aquí sí sumamos los minutos de adición SOLO para mostrar
        expected_minute_k += extra_minutes

        prob_k_goals_or_more = poisson_sf(k, mu_remaining)
        rows.append({
            "k (próximo #)": k,
            "Minuto esperado (con adición)": round(expected_minute_k, 1),
            f"Prob(≥ {k} goles antes del {int(match_duration_probs)}')": round(prob_k_goals_or_more, 4)
        })
    return pd.DataFrame(rows)

# --------------------------
# Interfaz Streamlit
# --------------------------
st.title("⚽ Ajuste de Goles con Poisson y Odds")

base_duration = st.number_input("Duración reglamentaria del partido", min_value=30.0, max_value=120.0, value=90.0, step=1.0)
extra_minutes = st.number_input("Minutos de adición / alargue (solo para mostrar en ⏱)", min_value=0.0, max_value=30.0, value=0.0, step=0.5)

# Duración solo para probabilidades (NO incluye adición)
match_duration_probs = base_duration

# Tabla editable para registrar goles
st.subheader("Registrar goles (minuto y cantidad)")
default_data = {"Minuto del gol": [], "Goles en ese minuto": []}
gol_data = st.data_editor(pd.DataFrame(default_data), num_rows="dynamic", use_container_width=True)

# Calcular total de goles y primer gol
if not gol_data.empty and gol_data["Goles en ese minuto"].sum() > 0:
    first_goal_min = gol_data[gol_data["Goles en ese minuto"] > 0]["Minuto del gol"].min()
    goals_so_far = int(gol_data["Goles en ese minuto"].sum())
else:
    first_goal_min = st.number_input("Minuto del primer gol", min_value=1.0, max_value=90.0, value=7.0, step=1.0)
    goals_so_far = 0

current_minute = st.number_input("Minuto actual del partido", min_value=0.0, max_value=match_duration_probs, value=23.0, step=1.0)

# --------------------------
# Ajuste λ
# --------------------------
if goals_so_far > 0:
    lam_total = match_duration_probs / first_goal_min
    lam_max = 6
    lam_total = min(lam_total, lam_max)
    if goals_so_far >= 3:
        lam_total *= 0.6
else:
    lam_total = 1.0  # default si no hay goles

# Barra de ajuste según odds (ampliada)
ajuste_factor = st.slider(
    "🔧 Ajuste respecto a odds (ej: +200% o -200%)", 
    min_value=-5.0,   # -500%
    max_value=5.0,    # +500%
    value=0.0, 
    step=0.01,
    help="Ajusta la expectativa de goles basado en las odds del mercado"
)
lam_total *= (1 + ajuste_factor)

# ✅ Control para la aceleración disponible SIEMPRE
acceleration_factor = st.slider(
    "🚀 Factor de aceleración de tiempo en segundo tiempo (%)", 
    min_value=0, 
    max_value=50, 
    value=50, 
    step=1,
    help="Reduce el tiempo estimado para los goles en el segundo tiempo. Ejemplo: 33% significa que un gol esperado al minuto 80 se anticipará al 68."
)

st.markdown(f"### λ ajustado con odds = **{lam_total:.2f}** goles esperados")
st.markdown(f"### Duración usada para probabilidades = **{match_duration_probs} minutos (sin adición)**")
st.markdown(f"### Minutos de adición solo aplicados a ⏱ visualización = **+{extra_minutes} min**")

# --------------------------
# Mostrar resultados
# --------------------------
st.subheader("📊 Over/Under condicionado al minuto actual")
ou_df = ou_table(lam_total, current_minute, goals_so_far, match_duration_probs)
st.dataframe(ou_df, use_container_width=True)

st.subheader("⏱ Próximos goles esperados (ajustados)")
next_df = next_goals(lam_total, current_minute, match_duration_probs, extra_minutes, acceleration_factor=acceleration_factor)
st.dataframe(next_df, use_container_width=True)

# Explicación del factor de aceleración y adición
if acceleration_factor > 0 or extra_minutes > 0:
    st.info(f"""
    **🔍 Nota sobre ajustes:**  
    - Factor de aceleración aplicado: **{acceleration_factor}%** en la segunda mitad.  
    - Los **{extra_minutes} minutos de adición** NO afectan las probabilidades, solo se suman a los minutos esperados en ⏱.  

    **Ejemplo con aceleración:**  
    Un gol esperado al minuto 80 ahora se anticipará al minuto 
    {round(45 + (80 - 45) * (1 - acceleration_factor/100) + extra_minutes, 1)} (incluyendo adición).  
    """)
