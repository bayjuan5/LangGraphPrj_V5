"""
Node 3 — Timed Petri Net: Temporal Immune-State Modelling
Encodes cell-state transitions across 8 developmental timepoints
(4–12 weeks of KSC mouse pancreatic cancer progression) using
a Timed Petri Net (TPN) whose firing rates are calibrated from
the protein_matrix produced by Node 2.1.

Input  state keys: protein_matrix, protein_channels, zone_labels,
                   immune_score, stromal_score
Output state keys: temporal_trajectory (dict), immune_states (list),
                   dominant_program_per_tp (list), tpn_summary (dict)
"""

import numpy as np

# ── Petri Net definition ─────────────────────────────────────────────────────
# Places (cell states) at each timepoint
PLACES = [
    "Naive_T",       # naive CD4/CD8 T cells
    "Activated_T",   # effector T cells (IFNg+, GZMB+)
    "Exhausted_T",   # PD1+, LAG3+, TIM3+
    "Treg",          # FOXP3+ regulatory T cells
    "M1_Macro",      # pro-inflammatory macrophages (CD68+, TNFa+)
    "M2_Macro",      # anti-inflammatory macrophages (CD163+, IL10+)
    "Fibroblast",    # FAP+, ColI+
    "Tumour_cell",   # PanCK+, Ki67+
]

# Timepoints (weeks) — 8 developmental stages
TIMEPOINTS = [4, 5, 6, 7, 8, 9, 11, 12]

# Transitions (firing rules): (source_place, target_place, base_rate)
TRANSITIONS = [
    ("Naive_T",       "Activated_T",  0.35),
    ("Activated_T",   "Exhausted_T",  0.20),
    ("Activated_T",   "Treg",         0.10),
    ("Naive_T",       "Treg",         0.08),
    ("M1_Macro",      "M2_Macro",     0.25),
    ("Fibroblast",    "Fibroblast",   0.05),  # self-renewal
    ("Tumour_cell",   "Tumour_cell",  0.40),  # proliferation
    ("Activated_T",   "Naive_T",      0.05),  # memory conversion
]


def _calibrate_rates(immune_score: float, stromal_score: float) -> dict:
    """Scale base firing rates using immune/stromal scores from ROSIE."""
    rates = {}
    for src, tgt, base in TRANSITIONS:
        key = f"{src}->{tgt}"
        if "Exhausted" in tgt:
            # Higher stromal pressure -> faster exhaustion
            rates[key] = base * (1.0 + stromal_score)
        elif "Activated" in tgt:
            # Higher immune score -> faster activation
            rates[key] = base * (1.0 + immune_score)
        elif "M2" in tgt:
            # Stromal niche drives M2 polarisation
            rates[key] = base * (1.0 + stromal_score * 0.8)
        elif "Tumour" in tgt:
            # Immune suppression allows tumour growth
            rates[key] = base * (1.0 + stromal_score - immune_score * 0.5)
        else:
            rates[key] = base
    return rates


def _simulate_tpn(initial_tokens: dict, rates: dict,
                  n_timepoints: int = 8, dt: float = 1.0) -> list:
    """
    Forward-simulate the Petri net using a continuous (rate-equation) ODE
    approximation over n_timepoints steps.
    Returns list of state vectors (one per timepoint).
    """
    places = list(PLACES)
    state  = np.array([initial_tokens.get(p, 0.0) for p in places], dtype=float)
    idx    = {p: i for i, p in enumerate(places)}
    trajectory = [state.copy()]

    for _ in range(n_timepoints - 1):
        delta = np.zeros(len(places))
        for src, tgt, _ in TRANSITIONS:
            key  = f"{src}->{tgt}"
            rate = rates.get(key, 0.1)
            flow = rate * state[idx[src]] * dt
            delta[idx[src]] -= flow
            if tgt != src:
                delta[idx[tgt]] += flow
        state = np.clip(state + delta, 0, None)
        # Normalise so total tokens are conserved
        total = state.sum()
        if total > 0:
            state = state / total
        trajectory.append(state.copy())

    return trajectory


def process(state, params=None):
    protein_matrix  = state.get("protein_matrix", [])
    protein_channels = state.get("protein_channels", [])
    zone_labels     = state.get("zone_labels", [])
    immune_score    = float(state.get("immune_score", 0.25))
    stromal_score   = float(state.get("stromal_score", 0.45))

    rng = np.random.default_rng(3)

    print("Timed Petri Net: modelling temporal immune trajectory")
    print(f"  Immune score  : {immune_score:.3f}")
    print(f"  Stromal score : {stromal_score:.3f}")

    # ── Initial token distribution calibrated from protein_matrix ────────────
    if protein_matrix:
        pm = np.array(protein_matrix, dtype=np.float32)
        ch = list(protein_channels)
        def mean_ch(*names):
            idxs = [ch.index(n) for n in names if n in ch]
            return float(pm[:, idxs].mean()) if idxs else 0.1

        initial_tokens = {
            "Naive_T":     mean_ch("CD3", "CD4", "CD8"),
            "Activated_T": mean_ch("GZMB", "IFNg"),
            "Exhausted_T": mean_ch("PD1", "LAG3", "TIM3"),
            "Treg":        mean_ch("FOXP3"),
            "M1_Macro":    mean_ch("CD68", "TNFa"),
            "M2_Macro":    mean_ch("CD163", "IL6"),
            "Fibroblast":  mean_ch("FAP", "ColI"),
            "Tumour_cell": mean_ch("PanCK", "Ki67"),
        }
    else:
        # Fallback for demo mode
        initial_tokens = {
            "Naive_T": 0.25, "Activated_T": 0.20, "Exhausted_T": 0.05,
            "Treg": 0.05,    "M1_Macro": 0.15,    "M2_Macro": 0.10,
            "Fibroblast": 0.10, "Tumour_cell": 0.10,
        }
        total = sum(initial_tokens.values())
        initial_tokens = {k: v / total for k, v in initial_tokens.items()}

    # Normalise tokens
    total = sum(initial_tokens.values())
    initial_tokens = {k: v / total for k, v in initial_tokens.items()}

    # ── Calibrate rates from ROSIE outputs ───────────────────────────────────
    rates = _calibrate_rates(immune_score, stromal_score)

    # ── Simulate ─────────────────────────────────────────────────────────────
    trajectory = _simulate_tpn(initial_tokens, rates, n_timepoints=len(TIMEPOINTS))

    # ── Build output ─────────────────────────────────────────────────────────
    temporal_trajectory = {}
    dominant_program_per_tp = []
    for i, (tp, tok_vec) in enumerate(zip(TIMEPOINTS, trajectory)):
        place_map = {PLACES[j]: float(round(tok_vec[j], 4))
                     for j in range(len(PLACES))}
        temporal_trajectory[f"week_{tp}"] = place_map
        dominant = PLACES[int(tok_vec.argmax())]
        dominant_program_per_tp.append({"week": tp, "dominant": dominant,
                                        "fraction": float(round(tok_vec.max(), 4))})

    # Summarise microenvironmental phases
    early_immune  = np.array([trajectory[i][PLACES.index("Activated_T")]
                              for i in range(3)]).mean()
    mid_mixed     = np.array([trajectory[i][PLACES.index("M2_Macro")]
                              for i in range(3, 6)]).mean()
    late_stromal  = np.array([trajectory[i][PLACES.index("Fibroblast")]
                              for i in range(6, 8)]).mean()

    tpn_summary = {
        "early_immune_activation": round(float(early_immune), 4),
        "mid_myeloid_transition":  round(float(mid_mixed), 4),
        "late_stromal_dominance":  round(float(late_stromal), 4),
        "n_timepoints":            len(TIMEPOINTS),
        "timepoints_weeks":        TIMEPOINTS,
        "places":                  PLACES,
    }

    print(f"Temporal trajectory across {len(TIMEPOINTS)} timepoints (wks {TIMEPOINTS[0]}–{TIMEPOINTS[-1]}):")
    for dp in dominant_program_per_tp:
        bar = "█" * int(dp["fraction"] * 20)
        print(f"  Wk {dp['week']:2d}  {dp['dominant']:15s}  {bar} {dp['fraction']:.3f}")
    print(f"Phase summary:")
    print(f"  Early immune activation : {early_immune:.3f}")
    print(f"  Mid myeloid transition  : {mid_mixed:.3f}")
    print(f"  Late stromal dominance  : {late_stromal:.3f}")

    state.update({
        "temporal_trajectory":      temporal_trajectory,
        "immune_states":            PLACES,
        "dominant_program_per_tp":  dominant_program_per_tp,
        "tpn_summary":              tpn_summary,
    })
    return state
