# app.py
import streamlit as st
import streamlit.components.v1 as components
import networkx as nx
from pyvis.network import Network
import random
import math

# Make sure your original code is in a file named simulation.py
try:
    from simulation import GraphSimulation, CATEGORY_COUNTS, TOTAL_POPULATION, INITIAL_INFECTED_PERCENTAGE, NODE_CATEGORIES
except ImportError:
    st.error("Error: Could not find the 'simulation.py' file. Please make sure it is in the same directory as app.py.")
    st.stop()

# --- Streamlit Page Configuration ---
st.set_page_config(layout="wide")
st.title("Interactive Graph Simulation of Infection Spread")

# --- NEW: Helper function to get color based on infection percentage ---
def get_infection_color(infected, total):
    """Returns a color from green to red based on the percentage of infection."""
    if total == 0:
        return "#808080"  # Gray for empty nodes
    
    percentage = infected / total
    
    # Interpolate between green (0%) and red (100%)
    # Green is (0, 128, 0), Red is (255, 0, 0)
    red = int(255 * percentage)
    green = int(128 * (1 - percentage))
    blue = 0
    
    return f"rgb({red},{green},{blue})"

# --- Helper function to generate the graph for a given state ---
@st.cache_data(show_spinner="Generating graph...")
def generate_pyvis_html(_simulation_state_dict, title):
    nodes_data = _simulation_state_dict['nodes']
    edges_data = _simulation_state_dict.get('edges', []) # NEW: Get edge data
    
    G = nx.DiGraph()

    # --- NEW: Define colors for destination categories for edges ---
    category_edge_colors = {
        'h': '#1f77b4', 'sh': '#ff7f0e', 'p': '#2ca02c', 's': '#d62728',
        'r': '#9467bd', 'c': '#8c564b', 't': '#e377c2', 'H': '#7f7f7f', 'o': '#bcbd22'
    }

    # Add nodes with new dynamic coloring
    for node_id, node_details in nodes_data.items():
        infected = node_details['population']['infected']
        non_infected = node_details['population']['non_infected']
        total_pop = infected + non_infected
        
        G.add_node(
            node_id,
            label=f"{node_id}",
            title=(f"Category: {NODE_CATEGORIES[node_details['category']]}  "f"Infected: {infected}  "f"Non-Infected: {non_infected}  "f"Total: {total_pop}"),
            # --- NEW: Use the green-to-red color scale ---
            color=get_infection_color(infected, total_pop),
            size=10 + total_pop / 2
        )

    # --- NEW: Add dynamic edges based on movement in the current turn ---
    for edge in edges_data:
        source, dest, weight = edge['source'], edge['dest'], edge['weight']
        dest_category = nodes_data[dest]['category']
        G.add_edge(
            source,
            dest,
            value=weight, # Edge width based on number of people
            title=f"{weight} people moved",
            color=category_edge_colors.get(dest_category, '#cccccc') # Edge color by destination type
        )

    net = Network(height="700px", width="100%", notebook=False, directed=True, bgcolor="#222222", font_color="white")
    net.from_nx(G)
    
    net.set_options("""
    var options = {
      "nodes": {
        "font": { "size": 16, "strokeWidth": 3, "strokeColor": "#222222" }
      },
      "edges": {
        "arrows": {
          "to": { "enabled": true, "scaleFactor": 0.5 }
        },
        "color": {
          "inherit": "to" 
        },
        "smooth": {
          "type": "continuous"
        }
      },
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -50,
          "centralGravity": 0.01,
          "springLength": 100
        },
        "minVelocity": 0.75,
        "solver": "forceAtlas2Based"
      }
    }
    """)
    
    try:
        html_string = net.generate_html()
        return html_string
    except Exception as e:
        return f"<p>Error generating graph: {e}</p>"

# --- Main Application Logic ---

st.sidebar.header("Simulation Controls")

if 'seed' not in st.session_state:
    st.session_state.seed = random.randint(0, 10000)

if st.sidebar.button("New Random Seed"):
    st.session_state.seed = random.randint(0, 10000)
    st.rerun()

st.sidebar.write(f"Current Seed: {st.session_state.seed}")

selected_day = st.sidebar.slider("Day", 0, 3, 0)
turn_options = {0: "Initial State", 1: "T1 (Work/School)", 2: "T2 (Social)", 3: "End of Day (Home)"}
selected_turn = st.sidebar.select_slider("Turn of Day", options=list(turn_options.keys()), value=0, format_func=lambda x: turn_options[x])

# --- Run Simulation up to the selected point ---
random.seed(st.session_state.seed)
temp_sim = GraphSimulation(CATEGORY_COUNTS, TOTAL_POPULATION, INITIAL_INFECTED_PERCENTAGE)

# --- NEW: Store movement data for visualization ---
movement_edges = []

# This is a simplified run-through; a more robust implementation would save state at each turn
if selected_day > 0:
    for day in range(1, selected_day + 1):
        is_target_day = (day == selected_day)
        
        # --- Turn 1 ---
        if is_target_day and selected_turn == 1: movement_edges.clear()
        locations_before_t1 = temp_sim.person_location.copy()
        temp_sim.turn1()
        temp_sim.apply_infection("T1")
        if is_target_day and selected_turn == 1:
            for pid, new_loc in temp_sim.person_location.items():
                movement_edges.append({'source': locations_before_t1[pid], 'dest': new_loc})
        if is_target_day and selected_turn == 1: break

        # --- Turn 2 ---
        if is_target_day and selected_turn == 2: movement_edges.clear()
        locations_before_t2 = temp_sim.person_location.copy()
        temp_sim.turn2()
        temp_sim.apply_infection("T2")
        if is_target_day and selected_turn == 2:
            for pid, new_loc in temp_sim.person_location.items():
                movement_edges.append({'source': locations_before_t2[pid], 'dest': new_loc})
        if is_target_day and selected_turn == 2: break

        # --- Turn 3 ---
        if is_target_day and selected_turn == 3: movement_edges.clear()
        locations_before_t3 = temp_sim.person_location.copy()
        temp_sim.turn3()
        temp_sim.apply_infection("T3")
        if is_target_day and selected_turn == 3:
            for pid, new_loc in temp_sim.person_location.items():
                movement_edges.append({'source': locations_before_t3[pid], 'dest': new_loc})
        if is_target_day and selected_turn == 3: break

# --- NEW: Aggregate edges for visualization ---
aggregated_edges = {}
for edge in movement_edges:
    key = (edge['source'], edge['dest'])
    aggregated_edges[key] = aggregated_edges.get(key, 0) + 1

final_edges_for_viz = [{'source': s, 'dest': d, 'weight': w} for (s, d), w in aggregated_edges.items()]

# --- Display the Visualization ---
st.header(f"Graph State: Day {selected_day}, {turn_options[selected_turn]}")

# Create a serializable state dictionary for caching
simulation_state_dict = {
    'nodes': {nid: {'population': node.population, 'category': node.category} for nid, node in temp_sim.nodes.items()},
    'edges': final_edges_for_viz # Pass the aggregated edges
}

graph_html = generate_pyvis_html(simulation_state_dict, f"Day {selected_day} Turn {selected_turn}")

with st.container():
    components.html(graph_html, height=750, scrolling=False)

# --- Display Raw Data ---
with st.expander("Show Node Population Data"):
    st.subheader("Node Populations")
    data_rows = []
    for node_id in sorted(temp_sim.nodes.keys()):
        node = temp_sim.nodes[node_id]
        total = node.population['infected'] + node.population['non_infected']
        if total > 0:
            data_rows.append({
                "Node": node_id,
                "Category": NODE_CATEGORIES[node.category],
                "Infected": node.population['infected'],
                "Non-Infected": node.population['non_infected'],
                "Total": total
            })
    if data_rows:
        st.dataframe(data_rows)
    else:
        st.write("No population present in any node at this step.")
