# app2.py
import streamlit as st
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
import random
import math
import copy

# Import the main Simulation class from your existing file
try:
    from simulation import Simulation
except ImportError:
    st.error("Error: Could not find `simulation.py`. Please make sure it is in the same directory.")
    st.stop()

st.set_page_config(layout="wide", page_title="Neighborhood Deep Dive")
st.title("Agent-Based Neighborhood Visualization")
st.write("A micro-level view of agent movement and status within a single neighborhood over a few days.")

# =============================================================================
# Helper Functions for Visualization
# =============================================================================

def get_disease_color(state):
    colors = {
        'susceptible': '#1f77b4', # Blue
        'exposed': '#ff7f0e',     # Orange
        'infectious': '#d62728', # Red
        'asymptomatic': '#e377c2', # Pink
        'removed': '#2ca02c',     # Green
        'dead': '#000000'         # Black
    }
    return colors.get(state, '#7f7f7f') # Gray for default

@st.cache_data(show_spinner="Generating graph...")
def generate_neighborhood_graph(_people_dict, _nodes_dict, _edges_list):
    """Generates a pyvis graph for the current state of the neighborhood."""
    net = Network(height="700px", width="100%", notebook=False, directed=True, bgcolor="#222222", font_color="white")

    # Add location nodes
    for node_id, node in _nodes_dict.items():
        net.add_node(node_id, label=node_id, color='#999999', shape='square', size=20)

    # Add person nodes
    for person_id, person in _people_dict.items():
        net.add_node(
            person_id,
            label=f"P{person_id[1:]}", # Short label
            color=get_disease_color(person.disease_state),
            size=10,
            shape='dot',
            title=f"ID: {person_id} | State: {person.disease_state} | Location: {person.location_id}"
        )
        # Add a "leash" edge from person to their location
        net.add_edge(person.location_id, person_id, color="#444444", physics=False, arrows='')

    # Add movement edges
    for edge in _edges_list:
        net.add_edge(edge['source'], edge['dest'], color=edge['color'], arrows='to', value=0.5)

    net.set_options("""
    var options = {
      "physics": { "barnesHut": { "gravitationalConstant": -10000, "springConstant": 0.05, "springLength": 150 } },
      "interaction": { "hover": true }
    }
    """)
    try:
        return net.generate_html()
    except Exception as e:
        return f"<p>Error generating graph: {e}</p>"

# =============================================================================
# Main App Logic
# =============================================================================

# --- Use session state to store the simulation timeline ---
if 'timeline' not in st.session_state:
    st.session_state.timeline = []

# --- Sidebar Controls ---
st.sidebar.header("Controls")
if st.sidebar.button("Run New Micro-Simulation"):
    # --- THIS IS THE CORRECTED SECTION ---

    # 1. Define the physics parameters first, just like in the main app.
    physics_params = {
        'E': 8.0,  # Default particle emission rate
        'rho': 1.3e-4, # Fixed breathing rate
        'categories': {}
    }
    default_volumes = {'h': 230, 'sh': 1500, 'p': 1000000, 's': 200, 'r': 800, 'c': 3000, 't': 5000, 'H': 400, 'o': 1000, 'st': 50000, 'pa': 300}
    default_achs = {'h': 0.5, 'sh': 4.0, 'p': 0.1, 's': 3.0, 'r': 8.0, 'c': 1.0, 't': 6.0, 'H': 12.0, 'o': 6.0, 'st': 8.0, 'pa': 2.0}
    for cat_code, ach in default_achs.items():
        physics_params['categories'][cat_code] = {
            'V': default_volumes.get(cat_code, 500),
            'lambda': ach / 3600.0 # Convert ACH to lambda (per second)
        }

    # 2. Define a small, fixed configuration for this deep-dive app
    config = {
        'total_population': 50,
        'age_of_population': 'medium',
        'percentage_infected': 0.1,
        'percentage_removed': 0.0,
        'infectivity': 0.1, # Higher infectivity to see spread quickly
        'time_of_incubation': 2,
        'time_of_activation': 5,
        'percentage_of_death': 0.0,
        'detection_of_disease_rate': 0.5,
        'physics_params': physics_params, # Add the complete physics dictionary
        'preventative_measures': {'vaccination_percentage': 0, 'vaccination_effectiveness': 0, 'quarantine_on_detection': False},
        'active_nodes': {cat: True for cat in ['o', 'sh', 'r', 'st', 'pa', 't', 'c', 's']},
        'public_transport_on': True
    }
    
    with st.spinner("Running new micro-simulation..."):
        sim = Simulation(config)
        
        # Store the initial state (Day 0, Turn 0)
        st.session_state.timeline = [{
            'day': 0, 'turn': 'Initial', 'people': copy.deepcopy(sim.people),
            'nodes': copy.deepcopy(sim.nodes), 'edges': []
        }]

        # Run for a few days and store the state at each turn
        for day in range(1, 3): # Run for 2 days
            # --- Work Turn ---
            prev_locations = {pid: p.location_id for pid, p in sim.people.items()}
            sim._move_and_infect('work')
            edges = [{'source': prev_locations[pid], 'dest': p.location_id, 'color': '#d62728'} for pid, p in sim.people.items() if prev_locations.get(pid) != p.location_id]
            st.session_state.timeline.append({'day': day, 'turn': 'Work', 'people': copy.deepcopy(sim.people), 'nodes': copy.deepcopy(sim.nodes), 'edges': edges})

            # --- Social Turn ---
            prev_locations = {pid: p.location_id for pid, p in sim.people.items()}
            sim._move_and_infect('social')
            edges = [{'source': prev_locations[pid], 'dest': p.location_id, 'color': '#9467bd'} for pid, p in sim.people.items() if prev_locations.get(pid) != p.location_id]
            st.session_state.timeline.append({'day': day, 'turn': 'Social', 'people': copy.deepcopy(sim.people), 'nodes': copy.deepcopy(sim.nodes), 'edges': edges})

            # --- Home Turn ---
            prev_locations = {pid: p.location_id for pid, p in sim.people.items()}
            sim._move_and_infect('home')
            edges = [{'source': prev_locations[pid], 'dest': p.location_id, 'color': '#1f77b4'} for pid, p in sim.people.items() if prev_locations.get(pid) != p.location_id]
            st.session_state.timeline.append({'day': day, 'turn': 'Home', 'people': copy.deepcopy(sim.people), 'nodes': copy.deepcopy(sim.nodes), 'edges': edges})
            
            sim._update_disease_progression() # Update disease state at end of day

    st.success("Micro-simulation complete!")
    st.rerun()

# --- Display Controls and Visualization ---
if not st.session_state.timeline:
    st.info("Click 'Run New Micro-Simulation' in the sidebar to begin.")
else:
    # Create a slider to navigate through the timeline
    num_steps = len(st.session_state.timeline)
    step_labels = [f"Day {s['day']} - {s['turn']}" for s in st.session_state.timeline]
    
    selected_step = st.select_slider(
        "Select Simulation Step",
        options=range(num_steps),
        format_func=lambda x: step_labels[x]
    )
    
    # Get the state for the selected step
    current_state = st.session_state.timeline[selected_step]
    
    st.header(f"State: {step_labels[selected_step]}")
    
    # Generate and display the graph
    graph_html = generate_neighborhood_graph(
        current_state['people'],
        current_state['nodes'],
        current_state['edges']
    )
    components.html(graph_html, height=720)
