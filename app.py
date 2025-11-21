# app.py
import streamlit as st
import pandas as pd
import math

# Import the main class from your updated simulation.py
try:
    from simulation import Simulation
except ImportError:
    st.error("Error: Could not find `simulation.py`. Please make sure it is in the same directory.")
    st.stop()

st.set_page_config(layout="wide", page_title="Comprehensive City Simulation")
st.title("Multi-Scale City Infection Sandbox")

# =============================================================================
# Sidebar for User Configuration
# =============================================================================
st.sidebar.header("Simulation Configuration")

with st.sidebar.form(key='config_form'):
    st.write("Set your parameters and click 'Run Simulation' at the bottom.")

    # --- Section 1: Population & Initial State ---
    with st.expander("Population & Initial State", expanded=True):
        total_population = st.slider("Total Population", 1000, 50000, 10000, 1000)
        age_of_population = st.selectbox("Population Age Structure", ['medium', 'young', 'old'])
        percentage_infected = st.slider("Initial Infected (%)", 0.0, 10.0, 1.0, 0.1) / 100.0
        percentage_removed = st.slider("Initial Immune/Removed (%)", 0.0, 50.0, 5.0, 1.0) / 100.0

    # --- Section 2: Disease Characteristics ---
    with st.expander("Disease Characteristics"):
        # The user-controlled infectivity 'gamma' from the formula
        infectivity = st.slider("Disease Infectivity (γ)", 0.001, 0.5, 0.05, 0.001, format="%.3f")
        time_of_incubation = st.slider("Incubation Time (days)", 1, 14, 3)
        time_of_activation = st.slider("Infection Duration (days)", 3, 30, 10)
        percentage_of_death = st.slider("Mortality Rate (%)", 0.0, 10.0, 1.0, 0.1) / 100.0
        detection_of_disease_rate = st.slider("Daily Detection Rate for Symptomatic (%)", 0.0, 100.0, 50.0, 1.0) / 100.0

    # --- NEW: Section 3: Environment & Physics ---
    with st.expander("Environment & Physics (Wells-Riley Model)"):
        st.write("These parameters control the physical spread of airborne particles.")
        emission_rate = st.slider("Particle Emission Rate (E)", 0.0, 0.2, 0.02, 0.001, help="Particles emitted per second by an infected person.")
        
        st.markdown("---")
        st.write("Ventilation Rate (Air Changes per Hour - ACH)")
        # We define default ACH values which the user can then override.
        default_achs = {'h': 0.5, 'sh': 4.0, 'p': 0.1, 's': 3.0, 'r': 8.0, 'c': 1.0, 't': 6.0, 'H': 12.0, 'o': 6.0, 'st': 8.0, 'pa': 2.0}
        ach_input = {}
        for cat_code, default_ach in default_achs.items():
            ach_input[cat_code] = st.slider(f"Ventilation for {cat_code.capitalize()}", 0.1, 60.0, default_ach, 0.1)
    
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
            active_nodes[cat] = st.checkbox(f"Allow {cat.capitalize()} to be open", True)
        public_transport_on = st.checkbox("Public Transport Open", True)

    # --- Section 5: Simulation Duration ---
    st.subheader("Simulation Duration")
    numb_of_days = st.slider("Number of Days to Simulate", 1, 100, 30)
    
    run_button = st.form_submit_button(label="Run Simulation")

# =============================================================================
# Main Application Logic
# =============================================================================

if 'simulation_instance' not in st.session_state:
    st.session_state.simulation_instance = None

if run_button:
    # --- Collate all user choices into a single config dictionary ---
    
    # 1. Build the physics_params dictionary from user inputs
    physics_params = {
        'E': emission_rate,
        'rho': 1.3e-4, # Breathing rate is fixed for this model
        'categories': {}
    }
    # Define default volumes for each category (these could also be sliders)
    default_volumes = {
        'h': 150,      # Home volume from your list
        'sh': 100,     # Shop volume
        'p': 1000000,  # Park remains very large (effectively open air)
        's': 200,      # School classroom volume
        'r': 200,      # Restaurant volume
        'c': 600,      # Church volume
        't': 1200,     # Theater volume
        'H': 400,      # Hospital room/ward volume
        'o': 1000,     # Office floor volume
        'st': 2000,    # Stadium section volume
        'pa': 400      # Party venue volume
    }
    for cat_code, ach in ach_input.items():
        physics_params['categories'][cat_code] = {
            'V': default_volumes.get(cat_code, 500), # Default volume if not specified
            'lambda': ach / 3600.0 # Convert ACH to lambda (per second)
        }

    # 2. Build the main config dictionary
    user_config = {
        'total_population': total_population,
        'age_of_population': age_of_population,
        'percentage_infected': percentage_infected,
        'percentage_removed': percentage_removed,
        'infectivity': infectivity, # This is now 'gamma' for the physics model
        'time_of_incubation': time_of_incubation,
        'time_of_activation': time_of_activation,
        'percentage_of_death': percentage_of_death,
        'detection_of_disease_rate': detection_of_disease_rate,
        'physics_params': physics_params, # Add the newly created dictionary
        'preventative_measures': {
            'vaccination_percentage': vaccination_percentage,
            'vaccination_effectiveness': vaccination_effectiveness,
            'quarantine_on_detection': quarantine_on_detection,
        },
        'subgroup_sizes': subgroup_sizes,
        'active_nodes': active_nodes,
        'public_transport_on': public_transport_on
    }
    
    # 3. Create and run the simulation
    with st.spinner(f"Running simulation for {numb_of_days} days... This may take a while for large populations."):
        sim = Simulation(user_config)
        for i in range(numb_of_days):
            sim.run_one_day()
        st.session_state.simulation_instance = sim
    st.success("Simulation Complete!")

# --- Display results if a simulation has been run ---
if st.session_state.simulation_instance:
    sim = st.session_state.simulation_instance
    
    st.header("Simulation Results")
    
    # Create and display the main chart
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
    
    # Display final numbers
    st.subheader("Final State")
    final_counts = sim.history[-1]
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Susceptible", f"{final_counts.get('susceptible', 0):,}")
    col2.metric("Total Exposed", f"{final_counts.get('exposed', 0):,}")
    col3.metric("Total Infectious (Active)", f"{final_counts.get('infectious', 0) + final_counts.get('asymptomatic', 0):,}")
    col4.metric("Total Removed/Immune", f"{final_counts.get('removed', 0):,}")
    st.metric("Total Deaths", f"{final_counts.get('dead', 0):,}")

else:
    st.info("Configure your simulation in the sidebar and click 'Run Simulation' to begin.")

if st.session_state.simulation_instance:
    st.subheader("Detailed Simulation Log")
    with st.expander("Click to see the turn-by-turn log"):
        # Use st.code to display the log in a fixed-width, scrollable box
        log_text = "\n".join(st.session_state.simulation_instance.log)
        st.code(log_text, language=None)