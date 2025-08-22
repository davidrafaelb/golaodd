# app.py
# -*- coding: utf-8 -*-
import math
import pandas as pd
import streamlit as st

# ===========================
# Funciones Poisson
# ===========================
def poisson_pmf(k, mu):
    return math.exp(-mu) * (mu ** k) / math.factorial(k)

def poisson_cdf(k, mu):
    return sum(poisson_pmf(i, mu) for i in range(k+1)) if k >= 0 else 0.0

def poisson_sf(k, mu):
    if k <= 0:
        return 1.0
    return 1.0 - poisson_cdf(k-1, mu)

# ===========================
# Over/Under condicional
# ===========================
def ou_table(lam_total, minute_now, goals_so_far, match_duration, max_line_half=8):
    rate_per_min = lam_total / match_duration
    remaining = max(0.0, match_duration - minute_now)
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

# ===========================
# Próximos goles esperados
# ===========================
def next_goals(lam_total, minute_now, match_duration, k_max=5):
    rate_per_min = lam_total / match_duration
    remaining = max(0.0, match_duration - minute_now)
    mu_remaining = rate_per_min * remaining

    rows = []
    for k in range(1, k_max+1):
        expected_wait_k = k / rate_per_min
        expected_minute_k = minute_now + expected_wait_k
        prob_k_goals_or_more = poisson_sf(k, mu_remaining)
        rows.append({
            "k (próximo #)": k,
            "Minuto esperado": round(expected_minute_k, 1),
            "Prob(≥ k goles antes del 90')": round(prob_k_goals_or_more, 4)
        })
    return pd.DataFrame(rows)

# ===========================
# Interfaz Streamlit
# ===========================
st.title("⚽ Estimación de Goles con Poisson")

# Entradas del usuario
first_goal_min = st.number_input("Minuto del primer gol", min_value=1.0, max_value=90.0, value=7.0, step=1.0)
current_minute = st.number_input("Minuto actual del partido", min_value=0.0, max_value=90.0, value=23.0, step=1.0)
goals_so_far = st.number_input("Goles ya ocurridos", min_value=0, max_value=20, value=2, step=1)
match_duration = st.number_input("Duración del partido", min_value=30.0, max_value=120.0, value=90.0, step=1.0)

# Estimar λ
lam_total = match_duration / first_goal_min
st.markdown(f"### λ estimado = **{lam_total:.2f}** goles esperados en {match_duration} minutos")

# Resultados
st.subheader("📊 Over/Under condicionado al minuto actual")
ou_df = ou_table(lam_total, current_minute, goals_so_far, match_duration)
st.dataframe(ou_df, use_container_width=True)

st.subheader("⏱ Próximos goles esperados")
next_df = next_goals(lam_total, current_minute, match_duration)
st.dataframe(next_df, use_container_width=True)
