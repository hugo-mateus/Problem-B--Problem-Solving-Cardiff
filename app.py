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
    Now tracks exposed, susceptible, and active infectious populations.
    """
    
    st.info(f"Starting Monte Carlo simulation with {num_runs} runs...")
    
    final_exposed_counts = []
    final_susceptible_counts = []
    final_infectious_counts = [] 

    progress_bar = st.progress(0)

    for i in range(num_runs):
        sim = Simulation(config)
        sim.run_simulation(days=num_days_to_simulate)
        final_results = sim.get_results()
        
        exposed_count = final_results.get('exposed', 0)
        susceptible_count = final_results.get('susceptible', 0)
        infectious_count = final_results.get('infectious', 0) + final_results.get('asymptomatic', 0)
        
        final_exposed_counts.append(exposed_count)
        final_susceptible_counts.append(susceptible_count)
        final_infectious_counts.append(infectious_count)
        
        progress_bar.progress((i + 1) / num_runs)

    st.success("Monte Carlo simulation complete!")

    def calculate_stats(data_array):
        mean = np.mean(data_array)
        ci = stats.t.interval(confidence=0.95, df=len(data_array)-1, loc=mean, scale=stats.sem(data_array))
        error_margin = (ci[1] - ci[0]) / 2.0 if not np.isnan(ci[0]) else 0.0
        return mean, error_margin, data_array.tolist()

    mean_exposed, error_margin_exposed, all_exposed = calculate_stats(np.array(final_exposed_counts))
    mean_susceptible, error_margin_susceptible, all_susceptible = calculate_stats(np.array(final_susceptible_counts))
    mean_infectious, error_margin_infectious, all_infectious = calculate_stats(np.array(final_infectious_counts))

    stats_results = {
        "exposed_mean": mean_exposed,
        "exposed_error_margin": error_margin_exposed,
        "exposed_all_runs": all_exposed,
        
        "susceptible_mean": mean_susceptible,
        "susceptible_error_margin": error_margin_susceptible,
        "susceptible_all_runs": all_susceptible,

        "infectious_mean": mean_infectious,
        "infectious_error_margin": error_margin_infectious,
        "infectious_all_runs": all_infectious
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
        infectivity = st.slider("Disease Infectivity (γ)", 0.0, 1.0, 0.5, 0.01, help="For Wells-Riley with quanta, this should be 1.0")
        time_of_incubation = st.slider("Incubation Time (days)", 1, 14, 3)
        time_of_activation = st.slider("Infection Duration (days)", 3, 30, 10)
        percentage_of_death = st.slider("Mortality Rate (%)", 0.0, 10.0, 0.3, 0.1) / 100.0
        detection_of_disease_rate = st.slider("Daily Detection Rate for Symptomatic (%)", 0.0, 100.0, 25.0, 1.0) / 100.0

    # --- Section 3: Environment & Physics ---
    with st.expander("Environment & Physics (Wells-Riley Model)"):
        st.write("Quanta Emission Rate (per HOUR)")
        E_low_hourly = st.number_input("Low Activity (Breathing)", value=0.002, min_value=0.0, step=0.001, format="%.3f")
        E_medium_hourly = st.number_input("Medium Activity (Speaking)", value=0.003, min_value=0.0, step=0.001, format="%.3f")
        E_high_hourly = st.number_input("High Activity (Singing/Shouting)", value=0.01, min_value=0.0, step=0.001, format="%.3f")
        
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
        # (Assuming other subgroup sliders would be here)

    with st.expander("Interventions & Policies"):
        vaccination_percentage = st.slider("Vaccination Coverage (%)", 0.0, 100.0, 0.0, 5.0) / 100.0
        vaccination_effectiveness = st.slider("Vaccine Effectiveness (%)", 0.0, 100.0, 90.0, 5.0) / 100.0
        quarantine_on_detection = st.checkbox("Enforce Quarantine on Detection", True)
    
    with st.expander("Lockdown Policies (Turn On/Off Locations)"):
        active_nodes = {}
        for cat in ['o', 'sh', 'r', 'st', 'pa', 't', 'c', 's']:
            active_nodes[cat] = st.checkbox(f"Allow {cat.upper()} to be open", True)
        public_transport_on = st.checkbox("Public Transport Open", True)

    st.subheader("Single Simulation Duration")
    numb_of_days = st.slider("Number of Days to Simulate", 1, 100, 30)
    
    run_button = st.form_submit_button(label="Run Single Simulation")

# =============================================================================
# Central function to gather UI settings
# =============================================================================
def get_config_from_ui():
    physics_params = {
        'rho': 1.3e-4,
        'E_hourly': {'low': E_low_hourly, 'medium': E_medium_hourly, 'high': E_high_hourly},
        'categories': {}
    }
    default_volumes = {'h': 150, 'sh': 100, 'p': 1000000, 's': 200, 'r': 200, 'c': 600, 't': 1200, 'H': 400, 'o': 1000, 'st': 2000, 'pa': 400}
    for cat_code, ach in ach_input.items():
        physics_params['categories'][cat_code] = {'V': default_volumes.get(cat_code, 500), 'lambda': ach / 3600.0}
    config = {
        'total_population': total_population, 'age_of_population': age_of_population,
        'percentage_infected': percentage_infected, 'percentage_removed': percentage_removed,
        'infectivity': infectivity, 'time_of_incubation': time_of_incubation,
        'time_of_activation': time_of_activation, 'percentage_of_death': percentage_of_death,
        'detection_of_disease_rate': detection_of_disease_rate, 'physics_params': physics_params,
        'preventative_measures': {'vaccination_percentage': vaccination_percentage, 'vaccination_effectiveness': vaccination_effectiveness, 'quarantine_on_detection': quarantine_on_detection},
        'subgroup_sizes': subgroup_sizes, 'active_nodes': active_nodes, 'public_transport_on': public_transport_on
    }
    return config

# =============================================================================
# Main Application Logic
# =============================================================================

# --- Monte Carlo Analysis Section ---
st.header("Monte Carlo Analysis")
st.markdown("Run the simulation multiple times to get an average outcome and error margin.")
num_mc_runs = st.number_input("Number of simulation runs", min_value=10, max_value=1000, value=15)
num_sim_days_mc = st.number_input("Number of days to simulate per run", min_value=1, max_value=100, value=30)

if st.button("Run Monte Carlo Analysis"):
    current_config = get_config_from_ui()
    analysis_results = run_monte_carlo(num_mc_runs, current_config, num_sim_days_mc)
    
    st.subheader("Analysis Results")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(label="Average Susceptible", value=f"{analysis_results['susceptible_mean']:.1f}", delta=f"± {analysis_results['susceptible_error_margin']:.1f}", delta_color="off")
    with col2:
        st.metric(label="Average Exposed", value=f"{analysis_results['exposed_mean']:.1f}", delta=f"± {analysis_results['exposed_error_margin']:.1f}", delta_color="off")
    with col3:
        st.metric(label="Average Active Infections", value=f"{analysis_results['infectious_mean']:.1f}", delta=f"± {analysis_results['infectious_error_margin']:.1f}", delta_color="off")
    
    st.subheader("Distribution of Outcomes")
    df_mc = pd.DataFrame({
        'Final Susceptible': analysis_results['susceptible_all_runs'],
        'Final Exposed': analysis_results['exposed_all_runs'],
        'Final Active Infections': analysis_results['infectious_all_runs']
    })
    st.bar_chart(df_mc)

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
    
    # --- START OF THE FIX ---
    # Define all possible states that should be in the chart
    all_states_to_plot = ['susceptible', 'exposed', 'infectious', 'asymptomatic', 'removed', 'dead']
    
    # Check for each state. If the column doesn't exist in the DataFrame, create it and fill with 0.
    for state in all_states_to_plot:
        if state not in history_df.columns:
            history_df[state] = 0
    # --- END OF THE FIX ---
            
    st.subheader("Disease State Over Time")
    # Now this line is safe, because we've guaranteed all the columns exist.
    st.line_chart(
        history_df,
        x='day',
        y=all_states_to_plot,
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
