# app.py
import streamlit as st
import streamlit.components.v1 as components
import networkx as nx
from pyvis.network import Network
import random
import math
import copy

# Make sure your original code is in a file named simulation.py
try:
    from simulation import GraphSimulation, NODE_CATEGORIES
except ImportError:
    st.error("Error: Could not find the 'simulation.py' file. Please make sure it is in the same directory as app.py.")
    st.stop()

# --- Streamlit Page Configuration ---
st.set_page_config(layout="wide")
st.title("Interactive Infection Spread Sandbox")

# =============================================================================
# --- Sidebar Configuration ---
# =============================================================================

# --- Part 1: Timeline Viewing Controls (These are always active) ---
st.sidebar.header("1. View Timeline")
# We need a default value for simulation_days if the config isn't set yet
total_sim_days = st.session_state.get('config', {}).get('simulation_days', 3)
selected_day = st.sidebar.slider("View Day", 0, total_sim_days, 0)
turn_options = {0: "Initial State", 1: "T1 (Work/School)", 2: "T2 (Social)", 3: "End of Day (Home)"}
selected_turn = st.sidebar.select_slider("View Turn of Day", options=list(turn_options.keys()), value=0, format_func=lambda x: turn_options[x])

# --- Part 2: Simulation Setup Form ---
st.sidebar.header("2. Configure and Run New Simulation")
with st.sidebar.form(key='config_form'):
    st.write("Set your parameters and click the button below.")

    # --- Population and Initial State ---
    with st.expander("Population and Initial State", expanded=True):
        total_population_input = st.slider("Total Population", 50, 500, 100, 10)
        initial_infected_percentage_input = st.slider("Initial Infected Percentage", 0.01, 0.5, 0.1, 0.01)

    # --- Node Counts ---
    with st.expander("Community Structure (Node Counts)"):
        category_counts_input = {}
        for cat_code, cat_name in NODE_CATEGORIES.items():
            category_counts_input[cat_code] = st.slider(
                f"Number of {cat_name.capitalize()}s", 0, 50, 40 if cat_code == 'h' else 2, 1
            )

    # --- Disease and Environment Parameters ---
    with st.expander("Disease and Environment Physics"):
        gamma_input = st.slider("Disease Infectivity (γ)", 0.001, 0.1, 0.01, 0.001, format="%.3f")
        emission_rate_input = st.slider("Particle Emission Rate (E)", 1.0, 20.0, 8.0, 0.5)
        st.markdown("---")
        st.write("Ventilation Rate (Air Changes per Hour)")
        ach_input = {}
        default_achs = {'h': 0.5, 'sh': 4.0, 'p': 50.0, 's': 3.0, 'r': 8.0, 'c': 1.0, 't': 6.0, 'H': 12.0, 'o': 6.0}
        for cat_code, cat_name in NODE_CATEGORIES.items():
            ach_input[cat_code] = st.slider(f"Ventilation for {cat_name.capitalize()}", 0.1, 60.0, default_achs[cat_code], 0.1)

    # --- Simulation Time ---
    simulation_days_input = st.slider("Total Simulation Days", 1, 30, 3)

    # --- The "Run" button that submits all the form data ---
    submitted = st.form_submit_button("Run / Update Simulation")


# --- Store submitted configurations in session_state ---
if submitted:
    st.session_state.config = {
        "total_population": total_population_input,
        "initial_infected_percentage": initial_infected_percentage_input,
        "category_counts": category_counts_input,
        "gamma": gamma_input,
        "emission_rate": emission_rate_input,
        "ach": ach_input,
        "simulation_days": simulation_days_input,
        "seed": random.randint(0, 10000) # Generate a new seed for each new run
    }
    st.cache_data.clear()
    st.success(f"New simulation configured with Seed: {st.session_state.config['seed']}. The timeline has been updated.")

# --- Stop if no configuration has been submitted yet ---
if 'config' not in st.session_state:
    st.info("Please configure your simulation in the sidebar and click 'Run / Update Simulation'.")
    st.stop()

# =============================================================================
# --- Main Application Logic (The rest of the file is the same) ---
# =============================================================================

# --- Helper Functions (Unchanged) ---
def get_infection_color(infected, total):
    if total == 0: return "#808080"
    percentage = infected / total
    red = int(255 * percentage)
    green = int(128 * (1 - percentage))
    return f"rgb({red},{green},0)"

@st.cache_data(show_spinner="Generating graph...")
def generate_pyvis_html(_simulation_state_dict, title):
    nodes_data = _simulation_state_dict['nodes']
    edges_data = _simulation_state_dict.get('edges', [])
    G = nx.DiGraph()
    category_edge_colors = {
        'h': '#1f77b4', 'sh': '#ff7f0e', 'p': '#2ca02c', 's': '#d62728',
        'r': '#9467bd', 'c': '#8c564b', 't': '#e377c2', 'H': '#7f7f7f', 'o': '#bcbd22'
    }
    for node_id, node_details in nodes_data.items():
        infected, non_infected = node_details['population']['infected'], node_details['population']['non_infected']
        total_pop = infected + non_infected
        G.add_node(
            node_id, label=f"{node_id}",
            title=(f"Category: {NODE_CATEGORIES.get(node_details['category'], 'Unknown')}  " f"Infected: {infected}  Non-Infected: {non_infected}  Total: {total_pop}"),
            color=get_infection_color(infected, total_pop), size=10 + total_pop / 2
        )
    for edge in edges_data:
        source, dest, weight = edge['source'], edge['dest'], edge['weight']
        dest_category = nodes_data[dest]['category']
        G.add_edge(
            source, dest, value=weight, title=f"{weight} people moved",
            color=category_edge_colors.get(dest_category, '#cccccc')
        )
    net = Network(height="700px", width="100%", notebook=False, directed=True, bgcolor="#222222", font_color="white")
    net.from_nx(G)
    net.set_options("""
    var options = {
      "nodes": { "font": { "size": 16, "strokeWidth": 3, "strokeColor": "#222222" } },
      "edges": { "arrows": { "to": { "enabled": true, "scaleFactor": 0.5 } }, "color": { "inherit": "to" }, "smooth": { "type": "continuous" } },
      "physics": { "forceAtlas2Based": { "gravitationalConstant": -50, "centralGravity": 0.01, "springLength": 100 }, "minVelocity": 0.75, "solver": "forceAtlas2Based" }
    }
    """)
    try:
        return net.generate_html()
    except Exception as e:
        return f"<p>Error generating graph: {e}</p>"

# --- Build the dynamic configurations from the stored state ---
config = st.session_state.config
random.seed(config['seed'])

PHYSICS_PARAMS = {
    'E': config['emission_rate'], 'rho': 1.3e-4, 'gamma': config['gamma'],
    'categories': {cat: {'ACH': ach} for cat, ach in config['ach'].items()}
}
default_volumes = {'h': 230, 'sh': 1500, 'p': 1000000, 's': 450, 'r': 800, 'c': 3000, 't': 5000, 'H': 400, 'o': 1000}
for cat_code in PHYSICS_PARAMS['categories']:
    PHYSICS_PARAMS['categories'][cat_code]['V'] = default_volumes[cat_code]
    PHYSICS_PARAMS['categories'][cat_code]['lambda'] = PHYSICS_PARAMS['categories'][cat_code]['ACH'] / 3600.0

import simulation
simulation.PHYSICS_PARAMS = PHYSICS_PARAMS

try:
    temp_sim = GraphSimulation(config['category_counts'], config['total_population'], config['initial_infected_percentage'])
except (ValueError, ZeroDivisionError) as e:
    st.error(f"Error initializing simulation: {e}. A common cause is setting the number of households to 0.")
    st.stop()

# --- Run simulation up to the selected point ---
movement_edges = []
duration_t1, duration_t2, duration_t3 = 8 * 3600, 4 * 3600, 12 * 3600

if selected_day > 0 or selected_turn > 0:
    temp_sim.apply_infection("Day 0, Initial Overnight", duration_t3)

if selected_day > 0:
    for day in range(1, selected_day + 1):
        is_target_day = (day == selected_day)
        
        if is_target_day and selected_turn == 1: movement_edges.clear()
        locations_before_t1 = temp_sim.person_location.copy()
        temp_sim.turn1(); temp_sim.apply_infection("T1", duration_t1)
        if is_target_day and selected_turn == 1:
            for pid, new_loc in temp_sim.person_location.items(): movement_edges.append({'source': locations_before_t1[pid], 'dest': new_loc})
            break

        if is_target_day and selected_turn == 2: movement_edges.clear()
        locations_before_t2 = temp_sim.person_location.copy()
        temp_sim.turn2(); temp_sim.apply_infection("T2", duration_t2)
        if is_target_day and selected_turn == 2:
            for pid, new_loc in temp_sim.person_location.items(): movement_edges.append({'source': locations_before_t2[pid], 'dest': new_loc})
            break

        if is_target_day and selected_turn == 3: movement_edges.clear()
        locations_before_t3 = temp_sim.person_location.copy()
        temp_sim.turn3(); temp_sim.apply_infection("T3", duration_t3)
        if is_target_day and selected_turn == 3:
            for pid, new_loc in temp_sim.person_location.items(): movement_edges.append({'source': locations_before_t3[pid], 'dest': new_loc})
            break

# --- Display logic (unchanged) ---
aggregated_edges = {}
for edge in movement_edges:
    key = (edge['source'], edge['dest'])
    aggregated_edges[key] = aggregated_edges.get(key, 0) + 1
final_edges_for_viz = [{'source': s, 'dest': d, 'weight': w} for (s, d), w in aggregated_edges.items()]

st.header(f"Graph State: Day {selected_day}, {turn_options[selected_turn]}")
simulation_state_dict = {
    'nodes': {nid: {'population': node.population, 'category': node.category} for nid, node in temp_sim.nodes.items()},
    'edges': final_edges_for_viz
}
graph_html = generate_pyvis_html(simulation_state_dict, f"Day {selected_day} Turn {selected_turn}")
with st.container():
    components.html(graph_html, height=750, scrolling=False)

with st.expander("Show Node Population Data"):
    # ... (data display code remains the same)

    st.subheader("Node Populations")
    data_rows = []
    for node_id in sorted(temp_sim.nodes.keys()):
        node = temp_sim.nodes[node_id]
        total = node.population['infected'] + node.population['non_infected']
        if total > 0:
            data_rows.append({
                "Node": node_id, "Category": NODE_CATEGORIES.get(node.category, 'Unknown'),
                "Infected": node.population['infected'], "Non-Infected": node.population['non_infected'], "Total": total
            })
    if data_rows:
        st.dataframe(data_rows)
    else:
        st.write("No population present in any node at this step.")
