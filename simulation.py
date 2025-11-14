import random
from collections import defaultdict

# --- Configuration ---
NODE_CATEGORIES = {
    'h': 'household',
    'sh': 'shop',
    'p': 'park',
    's': 'school',
    'r': 'restaurant',
    'c': 'church',
    't': 'theater',
    'H': 'hospital',
    'o': 'office'
}

# Define the number of nodes for each category for a simple example
# Total nodes N will be the sum of these counts.
CATEGORY_COUNTS = {
    'h': 40,  # 5 households
    'sh': 2, # 2 shops
    'p': 1,  # 1 park
    's': 2,  # 2 schools
    'r': 2,  # 2 restaurants
    'c': 1,  # 1 church
    't': 1,  # 1 theater
    'H': 1,  # 1 hospital
    'o': 2   # 2 offices
}

TOTAL_POPULATION = 100 # Total number of people in the simulation
INITIAL_INFECTED_PERCENTAGE = 0.1
SIMULATION_DAYS = 3 # New configuration for multi-day simulation

class Node:
    def __init__(self, node_id, category):
        self.id = node_id
        self.category = category
        # Population currently at this node (infected, non-infected)
        self.population = {'infected': 0, 'non_infected': 0}
        # Individual people at this node {person_id: status}
        self.people = {}

    def __repr__(self):
        return f"Node({self.id}, {self.category}, Pop: {self.population['infected'] + self.population['non_infected']})"

class GraphSimulation:
    def __init__(self, category_counts, total_population, initial_infected_percentage):
        self.category_counts = category_counts
        self.total_population = total_population
        self.initial_infected_percentage = initial_infected_percentage
        self.nodes = {}
        # Stores the original household of each person, which is crucial for T3
        self.person_to_household = {}
        self.person_location = {} # Tracks the current location of each person
        self.person_status = {} # Tracks the infection status of each person
        self.simulation_history = [] # New: To store total infected count over time
        self._initialize_nodes()
        self._initialize_population()

    def _initialize_nodes(self):
        node_id_counter = 0
        for category, count in self.category_counts.items():
            for i in range(count):
                node_id = f"{category}{i+1}"
                self.nodes[node_id] = Node(node_id, category)
                node_id_counter += 1
        self.node_ids = list(self.nodes.keys())
        self.household_ids = [nid for nid, node in self.nodes.items() if node.category == 'h']
        self.school_ids = [nid for nid, node in self.nodes.items() if node.category == 's']
        self.office_ids = [nid for nid, node in self.nodes.items() if node.category == 'o']
        self.work_school_ids = self.school_ids + self.office_ids
        self.other_ids = [nid for nid in self.node_ids if nid not in self.household_ids + self.work_school_ids]

    def _initialize_population(self):
        # Distribute the total population among the household nodes
        num_infected = int(self.total_population * self.initial_infected_percentage)
        num_non_infected = self.total_population - num_infected

        # Create a list of people with their status and assign a unique ID
        person_list = []
        for i in range(num_infected):
            person_list.append({'id': f"P{i}", 'status': 'infected'})
        for i in range(num_non_infected):
            person_list.append({'id': f"P{num_infected + i}", 'status': 'non_infected'})
        random.shuffle(person_list)

        # Assign people to households, ensuring each person starts at a household (h node)
        for i, person in enumerate(person_list):
            person_id = person["id"]
            status = person["status"]
            household_id = self.household_ids[i % len(self.household_ids)]
            self.person_to_household[person_id] = household_id
            self.person_location[person_id] = household_id
            self.person_status[person_id] = status # Persistently store status
            self.nodes[household_id].population[status] += 1
            self.nodes[household_id].people[person_id] = status

        print(f"Initialized with {num_infected} infected and {num_non_infected} non-infected people.")
        print(f"Total nodes: {len(self.nodes)}")

    def run_simulation(self, days):
        print("\n--- Initial State (Day 0, T0: All at Household) ---")
        self.print_node_populations()
        self.print_infection_chances("Day 0 Infection")
        self._record_history(0) # Record initial state

        for day in range(1, days + 1):
            print(f"\n==================== DAY {day} ====================")
            
            # --- Turn 1: Household to School/Office ---
            self.turn1()
            self.apply_infection(f"Day {day}, After Turn 1 Movement")
            self.print_infection_chances(f"Day {day}, After Turn 1 Infection")

            # --- Turn 2: Any to Any ---
            self.turn2()
            self.apply_infection(f"Day {day}, After Turn 2 Movement")
            self.print_infection_chances(f"Day {day}, After Turn 2 Infection")

            # --- Turn 3: Return to Household ---
            self.turn3()
            self.apply_infection(f"Day {day}, After Turn 3 Movement")
            self.print_infection_chances(f"Day {day}, After Turn 3 Infection")

            # Print final state of the day
            print(f"\n--- End of Day {day} State (All at Household) ---")
            self.print_node_populations()
            self._record_history(day) # Record end-of-day state

    def calculate_infection_chance(self, node):
        """
        Calculates the chance of infection at a given node.
        This is a placeholder function based on the node's category and population.
        The user can replace this with their specific equation.
        """
        infected = node.population['infected']
        total = node.population['infected'] + node.population['non_infected']

        if total == 0:
            return 0.0

        # Define a base transmission factor for each category
        # These are arbitrary values for demonstration, reflecting different risk levels
        # e.g., Hospital (H) has high factor, Park (p) has low factor.
        category_factors = {
            'h': 0.5,   # Household: Moderate risk (close contact)
            'sh': 0.4,  # Shop: Moderate risk
            'p': 0.1,   # Park: Low risk (open air)
            's': 0.7,   # School: High risk (crowded, close contact)
            'r': 0.6,   # Restaurant: High risk (indoor, no masks while eating)
            'c': 0.3,   # Church: Low to moderate risk
            't': 0.5,   # Theater: Moderate risk (indoor, long duration)
            'H': 0.9,   # Hospital: Very high risk
            'o': 0.6    # Office: High risk
        }

        # Get the factor for the node's category, default to 0.5 if not found
        factor = category_factors.get(node.category, 0.5)

        # Placeholder Equation:
        # Chance = (Infected / Total Population) * Category Factor
        # This represents the probability of an uninfected person contracting the infection
        # based on the proportion of infected people and the environment's risk factor.
        chance = (infected / total) * factor

        # Cap the chance at 1.0
        return min(chance, 1.0)

    def print_node_populations(self):
        for node_id in sorted(self.nodes.keys()):
            node = self.nodes[node_id]
            total = node.population['infected'] + node.population['non_infected']
            if total > 0:
                infection_chance = self.calculate_infection_chance(node)
                print(f"  {node.id} ({node.category}): Infected={node.population['infected']}, Non-Infected={node.population['non_infected']}, Total={total}, **Infection Chance={infection_chance:.4f}**")

    # T1, T2, T3 methods will be implemented in subsequent steps
    def turn1(self):
        print("\n--- Turn 1: Household to School/Office ---")

        # NOTE: Population is cleared and recalculated in _recalculate_node_populations after infection step.
        # For T1, we assume everyone starts at their household (T0/T3 state)
        # We don't need to clear the nodes here, as the movement logic will overwrite the population.
        # However, to be safe and ensure the movement is clean, we will clear the nodes before movement.
        for node in self.nodes.values():
            node.population = {'infected': 0, 'non_infected': 0}
            node.people = {}

        # 2. Define possible destinations (Schools and Offices)
        destinations = self.school_ids + self.office_ids
        if not destinations:
            print("No schools or offices defined. T1 movement skipped.")
            return

        # 3. Simulate movement for each person
        # We need to track the movement for the edge weight (i, n)
        movement_counts = defaultdict(lambda: {'infected': 0, 'non_infected': 0})

        for person_id, household_id in self.person_to_household.items():
            status = self.person_status[person_id]

            # A person moves from their household to a random school or office
            destination_id = random.choice(destinations)

            # Update person's location
            self.person_location[person_id] = destination_id

            # Update destination node's population
            self.nodes[destination_id].population[status] += 1
            self.nodes[destination_id].people[person_id] = status

            # Update movement counts for the edge weight (i, n)
            # The edge is from the household to the destination
            edge_key = (household_id, destination_id)
            if status == 'infected':
                movement_counts[edge_key]['infected'] += 1
            else:
                movement_counts[edge_key]['non_infected'] += 1

        # 4. Print the edge weights (i, n)
        print("\n  Movement Edge Weights (Household -> School/Office):")
        for (source, dest), counts in movement_counts.items():
            i = counts['infected']
            n = counts['non_infected']
            if i + n > 0:
                print(f"    {source} -> {dest}: ({i}, {n})")

        print("\n  State after T1:")
        self.print_node_populations()

    def turn2(self):
        print("\n--- Turn 2: Any to Any ---")

        # 1. Clear population from all nodes (as everyone is moving)
        for node in self.nodes.values():
            node.population = {'infected': 0, 'non_infected': 0}
            node.people = {}

        # 2. Simulate movement for each person
        for person_id, current_location in self.person_location.items():
            status = self.person_status[person_id]


            # A person moves from their current node to a random node (complete graph)
            destination_id = random.choice(self.node_ids)

            # Update person's location
            self.person_location[person_id] = destination_id

            # Update destination node's population
            self.nodes[destination_id].population[status] += 1
            self.nodes[destination_id].people[person_id] = status

        print("\n  State after T2:")
        self.print_node_populations()

    def apply_infection(self, title):
        print(f"\n--- Applying Stochastic Infection: {title} ---")
        newly_infected_count = 0
        
        # 1. Iterate through all nodes to apply infection chance
        for node_id, node in self.nodes.items():
            total = node.population['infected'] + node.population['non_infected']
            if total == 0:
                continue

            # Calculate the chance of infection at this node
            infection_chance = self.calculate_infection_chance(node)
            
            # Identify non-infected people at this node
            non_infected_people = [
                person_id for person_id, status in node.people.items() 
                if status == 'non_infected'
            ]
            
            num_non_infected = len(non_infected_people)
            
            if num_non_infected == 0 or infection_chance == 0.0:
                continue

            # Determine how many people get infected (stochastic part)
            # Each non-infected person has a probability 'infection_chance' of getting infected.
            # We use a binomial distribution (or simply random.random() for each person)
            
            newly_infected_at_node = 0
            for person_id in non_infected_people:
                if random.random() < infection_chance:
                    # Person gets infected!
                    self.person_status[person_id] = 'infected'
                    newly_infected_at_node += 1
                    newly_infected_count += 1
            
            if newly_infected_at_node > 0:
                print(f"  {node_id} ({node.category}): {newly_infected_at_node} new infections (Chance: {infection_chance:.4f})")

        print(f"Total newly infected in this step: {newly_infected_count}")
        
        # 2. Re-calculate node populations to reflect the new statuses
        self._recalculate_node_populations()

    def _recalculate_node_populations(self):
        """Clears all node populations and re-populates them based on current person_location and person_status."""
        # Clear all nodes
        for node in self.nodes.values():
            node.population = {'infected': 0, 'non_infected': 0}
            node.people = {}
            
        # Re-populate nodes
        for person_id, location_id in self.person_location.items():
            status = self.person_status[person_id]
            node = self.nodes[location_id]
            node.population[status] += 1
            node.people[person_id] = status

    def print_infection_chances(self, title):
        print(f"\n--- Infection Chance Calculation: {title} ---")
        for node_id in sorted(self.nodes.keys()):
            node = self.nodes[node_id]
            total = node.population['infected'] + node.population['non_infected']
            if total > 0:
                chance = self.calculate_infection_chance(node)
                print(f"  {node.id} ({node.category}): Chance={chance:.4f}")

    def _record_history(self, day):
        """Records the total number of infected people at the end of a day."""
        total_infected = sum(1 for status in self.person_status.values() if status == 'infected')
        self.simulation_history.append({'day': day, 'total_infected': total_infected})

    def visualize_infection_spread(self):
        """Plots the total number of infected people over the simulation days."""
        import matplotlib.pyplot as plt
        
        days = [h['day'] for h in self.simulation_history]
        infected_counts = [h['total_infected'] for h in self.simulation_history]
        
        plt.figure(figsize=(10, 6))
        plt.plot(days, infected_counts, marker='o', linestyle='-', color='red')
        plt.title('Infection Spread Over Time')
        plt.xlabel('Day')
        plt.ylabel('Total Infected People')
        plt.grid(True)
        plt.xticks(days)
        
        # Save the plot to a file
        plot_filename = 'infection_spread_plot.png'
        plt.savefig(plot_filename)
        print(f"\n--- Visualization Saved ---")
        print(f"Infection spread plot saved to {plot_filename}")
        
        return plot_filename

    def turn3(self):
        print("\n--- Turn 3: Return to Household ---")

        # 1. Clear population from all nodes (as everyone is moving)
        for node in self.nodes.values():
            node.population = {"infected": 0, "non_infected": 0}
            node.people = {}

        # 2. Simulate movement for each person
        for person_id, household_id in self.person_to_household.items():
            status = self.person_status[person_id]

            # The person returns to their original household
            destination_id = household_id

            # Update person's location
            self.person_location[person_id] = destination_id

            # Update destination node's population
            self.nodes[destination_id].population[status] += 1
            self.nodes[destination_id].people[person_id] = status

        print("\n  State after T3 (All back at households):")
        self.print_node_populations()


# Add this method inside your GraphSimulation class
    def visualize_graph_structure(self, filename="graph_structure.html"):
        """
        Creates an interactive HTML visualization of the graph structure using pyvis.
        """
        import networkx as nx
        from pyvis.network import Network

        # 1. Create a networkx graph
        G = nx.Graph()

        # Define colors for each category for better visualization
        category_colors = {
            'h': '#1f77b4',   # Blue
            'sh': '#ff7f0e',  # Orange
            'p': '#2ca02c',   # Green
            's': '#d62728',   # Red
            'r': '#9467bd',   # Purple
            'c': '#8c564b',   # Brown
            't': '#e377c2',   # Pink
            'H': '#7f7f7f',   # Gray
            'o': '#bcbd22'    # Olive
        }

        # 2. Add nodes to the graph with properties
        for node_id, node in self.nodes.items():
            total_pop = node.population['infected'] + node.population['non_infected']
            G.add_node(
                node.id,
                label=f"{node.id}",
                title=f"Category: {NODE_CATEGORIES[node.category]} Initial Population: {total_pop}",
                color=category_colors.get(node.category, '#000000'),
                size=10 + total_pop / 2 # Node size based on population
            )

        # 3. Add edges to represent potential movement paths
        # We'll create a complete graph for Turn 2 and specific edges for Turn 1
        
        # Edges for Turn 1 (Household -> Work/School)
        for household_id in self.household_ids:
            for dest_id in self.work_school_ids:
                G.add_edge(household_id, dest_id, color='#d3d3d3', physics=False, title="T1 Path")

        # Edges for Turn 2 (Any -> Any, a complete graph)
        # For simplicity, we can assume all nodes are connected.
        # Pyvis will handle the layout. If we add all edges, it becomes a hairball.
        # A better approach is to show the *structure* based on categories.
        # Let's connect all non-household nodes to each other.
        non_household_ids = [nid for nid in self.node_ids if nid not in self.household_ids]
        for i in range(len(non_household_ids)):
            for j in range(i + 1, len(non_household_ids)):
                G.add_edge(non_household_ids[i], non_household_ids[j], color='#e0e0e0', physics=False, title="T2 Path")


        # 4. Create a pyvis network
        net = Network(height="800px", width="100%", notebook=False, directed=False, bgcolor="#222222", font_color="white")
        net.from_nx(G)

        # 5. Add options for interactivity and layout
        net.set_options("""
        var options = {
        "nodes": {
            "font": {
            "size": 16
            }
        },
        "edges": {
            "color": {
            "inherit": true
            },
            "smooth": false
        },
        "physics": {
            "forceAtlas2Based": {
            "gravitationalConstant": -50,
            "centralGravity": 0.01,
            "springLength": 100,
            "springConstant": 0.08
            },
            "minVelocity": 0.75,
            "solver": "forceAtlas2Based"
        }
        }
        """)

        # 6. Generate the HTML file
        net.save_graph(filename)
        print(f"\n--- Graph Visualization Saved ---")
        print(f"Interactive graph structure saved to {filename}")
        return filename



if __name__ == "__main__":
    sim = GraphSimulation(CATEGORY_COUNTS, TOTAL_POPULATION, INITIAL_INFECTED_PERCENTAGE)
    sim.run_simulation(SIMULATION_DAYS)
    
    sim.visualize_graph_structure()
