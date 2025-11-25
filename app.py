import streamlit as st
import pandas as pd
import math
import numpy as np
import scipy.stats as stats

# Import the main class from your updated simulation.py
try:
    from simulation import Simulation
except ImportError:
    st.error("Error: Could not find `simulation.py`. Please make sure it is in the same directory.")
    st.stop()

st.set_page_config(layout="wide", page_title="Comprehensive City Simulation")
st.title("Multi-Scale City Infection Sandbox")


def run_monte_carlo(num_runs, config, num_days_to_simulate):
    """
    Runs a Monte Carlo simulation for a given configuration.

    Args:
        num_runs (int): The number of times to run the simulation (e.g., 100).
        config (dict): The configuration dictionary for the simulation.
        num_days_to_simulate (int): The number of days each simulation run should last.

    Returns:
        dict: A dictionary containing the mean, standard deviation, and confidence interval.
    """
    
    st.info(f"Starting Monte Carlo simulation with {num_runs} runs...")
    
    final_exposed_counts = []
    progress_bar = st.progress(0)

    for i in range(num_runs):
        sim = Simulation(config)
        sim.run_simulation(days=num_days_to_simulate)
        final_results = sim.get_results()
        exposed_count = final_results.get('exposed', 0)
        final_exposed_counts.append(exposed_count)
        progress_bar.progress((i + 1) / num_runs)

    st.success("Monte Carlo simulation complete!")

    results_array = np.array(final_exposed_counts)
    mean_exposed = np.mean(results_array)
    std_dev_exposed = np.std(results_array)
    
    confidence_interval = stats.t.interval(
        confidence=0.95,
        df=len(results_array) - 1,
        loc=mean_exposed,
        scale=stats.sem(results_array)
    )
    
    if np.isnan(confidence_interval[0]) or np.isnan(confidence_interval[1]):
        error_margin = 0.0
    else:
        error_margin = (confidence_interval[1] - confidence_interval[0]) / 2.0

    stats_results = {
        "mean": mean_exposed,
        "std_dev": std_dev_exposed,
        "confidence_interval_95": confidence_interval,
        "error_margin": error_margin,
        "all_runs": final_exposed_counts
    }
    
    return stats_results

# =============================================================================
# Sidebar for User Configuration
# =============================================================================
st.sidebar.header("Simulation Configuration")

with st.sidebar.form(key='config_form'):
    st.write("Set your parameters and click a 'Run' button on the main page.")

    # --- Section 1: Population & Initial State ---
    with st.expander("Population & Initial State", expanded=True):
        total_population = st.slider("Total Population", 1000, 50000, 10000, 1000)
        age_of_population = st.selectbox("Population Age Structure", ['medium', 'young', 'old'])
        percentage_infected = st.slider("Initial Infected (%)", 0.0, 10.0, 0.5, 0.1) / 100.0
        percentage_removed = st.slider("Initial Immune/Removed (%)", 0.0, 50.0, 0.0, 1.0) / 100.0

    # --- Section 2: Disease Characteristics ---
    with st.expander("Disease Characteristics"):
        infectivity = st.slider("Disease Infectivity (γ)", 0.0, 1.0, 0.2, 0.01, help="For Wells-Riley with quanta, this should be 1.0")
        time_of_incubation = st.slider("Incubation Time (days)", 1, 14, 3)
        time_of_activation = st.slider("Infection Duration (days)", 3, 30, 10)
        percentage_of_death = st.slider("Mortality Rate (%)", 0.0, 10.0, 0.3, 0.1) / 100.0
        detection_of_disease_rate = st.slider("Daily Detection Rate for Symptomatic (%)", 0.0, 100.0, 25.0, 1.0) / 100.0

    # --- Section 3: Environment & Physics ---
    with st.expander("Environment & Physics (Wells-Riley Model)"):
        st.write("Quanta Emission Rate (per HOUR)")
        E_low_hourly = st.number_input("Low Activity (Breathing)", value=0.01, min_value=0.0)
        E_medium_hourly = st.number_input("Medium Activity (Speaking)", value=0.05, min_value=0.0)
        E_high_hourly = st.number_input("High Activity (Singing/Shouting)", value=0.1, min_value=0.0)
        
        st.markdown("---")
        st.write("Ventilation Rate (Air Changes per Hour - ACH)")
        default_achs = {'h': 0.5, 'sh': 5.0, 'p': 0.1, 's': 3.0, 'r': 4.0, 'c': 1.0, 't': 6.0, 'H': 6.0, 'o': 2.0, 'st': 8.0, 'pa': 2.0}
        ach_input = {}
        for cat_code, default_ach in default_achs.items():
            ach_input[cat_code] = st.slider(f"Ventilation for {cat_code.upper()}", 0.1, 20.0, default_ach, 0.1)
    
    with st.expander("Room/Group Sizes"):
        st.write("Control how many people mix in large locations.")
        subgroup_sizes = {}
        subgroup_sizes['s'] = st.slider("People per Classroom (Schools)", 10, 100, 30, 5)
        subgroup_sizes['o'] = st.slider("People per Floor (Offices)", 10, 200, 50, 5)
        subgroup_sizes['r'] = st.slider("People per Section (Restaurants)", 4, 50, 20, 2)
        subgroup_sizes['H'] = st.slider("People per Ward (Hospitals)", 2, 50, 15, 1)
        subgroup_sizes['st'] = st.slider("People per Section (Stadiums)", 20, 500, 100, 10)
        subgroup_sizes['pa'] = st.slider("People per Group (Parties)", 10, 100, 40, 5)
        subgroup_sizes['t'] = st.slider("People per Section (Theaters)", 20, 200, 75, 5)
        subgroup_sizes['c'] = st.slider("People per Group (Churches)", 10, 100, 50, 5)

    # --- Section 4: Interventions & Policies ---
    with st.expander("Interventions & Policies"):
        vaccination_percentage = st.slider("Vaccination Coverage (%)", 0.0, 100.0, 0.0, 5.0) / 100.0
        vaccination_effectiveness = st.slider("Vaccine Effectiveness (%)", 0.0, 100.0, 90.0, 5.0) / 100.0
        quarantine_on_detection = st.checkbox("Enforce Quarantine on Detection", True)
    
    with st.expander("Lockdown Policies (Turn On/Off Locations)"):
        active_nodes = {}
        for cat in ['o', 'sh', 'r', 'st', 'pa', 't', 'c', 's']:
            active_nodes[cat] = st.checkbox(f"Allow {cat.upper()} to be open", True)
        public_transport_on = st.checkbox("Public Transport Open", True)

    # --- Section 5: Simulation Duration ---
    st.subheader("Single Simulation Duration")
    numb_of_days = st.slider("Number of Days to Simulate", 1, 100, 3)
    
    run_button = st.form_submit_button(label="Run Single Simulation")

# =============================================================================
# Central function to gather UI settings
# =============================================================================
def get_config_from_ui():
    """Gathers all settings from the Streamlit UI and returns a config dictionary."""
    
    physics_params = {
        'rho': 1.3e-4,
        'E_hourly': {
            'low': E_low_hourly,
            'medium': E_medium_hourly,
            'high': E_high_hourly
        },
        'categories': {}
    }
    default_volumes = {
        'h': 150, 'sh': 100, 'p': 1000000, 's': 200, 'r': 200, 'c': 600,
        't': 1200, 'H': 400, 'o': 1000, 'st': 2000, 'pa': 400
    }
    for cat_code, ach in ach_input.items():
        physics_params['categories'][cat_code] = {
            'V': default_volumes.get(cat_code, 500),
            'lambda': ach / 3600.0
        }

    config = {
        'total_population': total_population,
        'age_of_population': age_of_population,
        'percentage_infected': percentage_infected,
        'percentage_removed': percentage_removed,
        'infectivity': infectivity,
        'time_of_incubation': time_of_incubation,
        'time_of_activation': time_of_activation,
        'percentage_of_death': percentage_of_death,
        'detection_of_disease_rate': detection_of_disease_rate,
        'physics_params': physics_params,
        'preventative_measures': {
            'vaccination_percentage': vaccination_percentage,
            'vaccination_effectiveness': vaccination_effectiveness,
            'quarantine_on_detection': quarantine_on_detection,
        },
        'subgroup_sizes': subgroup_sizes,
        'active_nodes': active_nodes,
        'public_transport_on': public_transport_on
    }
    return config

# =============================================================================
# Main Application Logic
# =============================================================================

# --- Monte Carlo Analysis Section ---
st.header("Monte Carlo Analysis")
st.markdown("Run the simulation multiple times to get an average outcome and error margin.")
num_mc_runs = st.number_input("Number of simulation runs", min_value=10, max_value=1000, value=100)
num_sim_days_mc = st.number_input("Number of days to simulate per run", min_value=1, max_value=100, value=3)

if st.button("Run Monte Carlo Analysis"):
    current_config = get_config_from_ui()
    analysis_results = run_monte_carlo(num_mc_runs, current_config, num_sim_days_mc)
    
    st.subheader("Analysis Results")
    mean = analysis_results['mean']
    error = analysis_results['error_margin']
    
    st.metric(
        label="Average Exposed People (at end of simulation)",
        value=f"{mean:.1f}",
        delta=f"± {error:.1f} (95% confidence)",
        delta_color="off"
    )
    st.write(f"Standard Deviation: **{analysis_results['std_dev']:.2f}**")
    
    st.subheader("Distribution of Outcomes")
    df = pd.DataFrame(analysis_results['all_runs'], columns=["Final Exposed Count"])
    st.bar_chart(df)

st.markdown("---")

# --- Single Simulation Run Logic ---
if 'simulation_instance' not in st.session_state:
    st.session_state.simulation_instance = None

if run_button:
    user_config = get_config_from_ui()
    
    with st.spinner(f"Running simulation for {numb_of_days} days..."):
        sim = Simulation(user_config)
        sim.run_simulation(days=numb_of_days)
        st.session_state.simulation_instance = sim
    st.success("Single Simulation Complete!")

# --- Display results if a simulation has been run ---
if st.session_state.simulation_instance:
    sim = st.session_state.simulation_instance
    
    st.header("Single Simulation Results")
    
    history_df = pd.DataFrame(sim.history)
    history_df['day'] = range(1, len(history_df) + 1)
    
    for state in ['susceptible', 'exposed', 'infectious', 'asymptomatic', 'removed', 'dead']:
        if state not in history_df.columns:
            history_df[state] = 0
            
    st.subheader("Disease State Over Time")
    st.line_chart(
        history_df,
        x='day',
        y=['susceptible', 'exposed', 'infectious', 'asymptomatic', 'removed', 'dead'],
        color=['#1f77b4', '#ff7f0e', '#d62728', '#e377c2', '#2ca02c', '#000000']
    )
    
    st.subheader("Final State")
    final_counts = sim.history[-1]
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Susceptible", f"{final_counts.get('susceptible', 0):,}")
    col2.metric("Total Exposed", f"{final_counts.get('exposed', 0):,}")
    col3.metric("Total Infectious (Active)", f"{final_counts.get('infectious', 0) + final_counts.get('asymptomatic', 0):,}")
    col4.metric("Total Removed/Immune", f"{final_counts.get('removed', 0):,}")
    st.metric("Total Deaths", f"{final_counts.get('dead', 0):,}")

    st.subheader("Detailed Simulation Log")
    with st.expander("Click to see the turn-by-turn log"):
        log_text = "\n".join(st.session_state.simulation_instance.log)
        st.code(log_text, language=None)

else:
    st.info("Configure your simulation in the sidebar and click 'Run Single Simulation' or 'Run Monte Carlo Analysis' to begin.")