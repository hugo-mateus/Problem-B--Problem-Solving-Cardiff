import random
from collections import defaultdict
import math # Import math at the top

# --- Configuration ---
NODE_CATEGORIES = {
    'h': 'household', 'sh': 'shop', 'p': 'park', 's': 'school',
    'r': 'restaurant', 'c': 'church', 't': 'theater', 'H': 'hospital', 'o': 'office'
}

CATEGORY_COUNTS = {
    'h': 40, 'sh': 2, 'p': 1, 's': 2, 'r': 2, 'c': 1, 't': 1, 'H': 1, 'o': 2
}

PHYSICS_PARAMS = {
    'E': 8.0, 'rho': 1.3e-4, 'gamma': 0.01,
    'categories': {
        'h': {'V': 230, 'lambda': 0.00014}, 'sh': {'V': 1500, 'lambda': 0.00111},
        'p': {'V': 1000000, 'lambda': 0.01389}, 's': {'V': 450, 'lambda': 0.00083},
        'r': {'V': 800, 'lambda': 0.00222}, 'c': {'V': 3000, 'lambda': 0.00028},
        't': {'V': 5000, 'lambda': 0.00167}, 'H': {'V': 400, 'lambda': 0.00333},
        'o': {'V': 1000, 'lambda': 0.00167},
    }
}

TOTAL_POPULATION = 100
INITIAL_INFECTED_PERCENTAGE = 0.01
SIMULATION_DAYS = 3

class Node:
    def __init__(self, node_id, category):
        self.id = node_id
        self.category = category
        self.population = {'infected': 0, 'non_infected': 0}
        self.people = {}

    def __repr__(self):
        return f"Node({self.id}, {self.category}, Pop: {self.population['infected'] + self.population['non_infected']})"

class GraphSimulation:
    def __init__(self, category_counts, total_population, initial_infected_percentage):
        self.category_counts = category_counts
        self.total_population = total_population
        self.initial_infected_percentage = initial_infected_percentage
        self.nodes = {}
        self.person_to_household = {}
        self.person_location = {}
        self.person_status = {}
        self.simulation_history = []
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
        num_infected = int(self.total_population * self.initial_infected_percentage)
        num_non_infected = self.total_population - num_infected
        person_list = [{'id': f"P{i}", 'status': 'infected'} for i in range(num_infected)]
        person_list.extend([{'id': f"P{num_infected + i}", 'status': 'non_infected'} for i in range(num_non_infected)])
        random.shuffle(person_list)

        for i, person in enumerate(person_list):
            person_id, status = person["id"], person["status"]
            household_id = self.household_ids[i % len(self.household_ids)]
            self.person_to_household[person_id] = household_id
            self.person_location[person_id] = household_id
            self.person_status[person_id] = status
            self.nodes[household_id].population[status] += 1
            self.nodes[household_id].people[person_id] = status

        print(f"Initialized with {num_infected} infected and {num_non_infected} non-infected people.")
        print(f"Total nodes: {len(self.nodes)}")

    def calculate_infection_probability(self, node, duration_seconds):
        category = node.category
        params = PHYSICS_PARAMS['categories'].get(category)
        if not params: return 0.0

        V, lambda_rate = params['V'], params['lambda']
        N_I = node.population['infected']
        E, rho, gamma, t = PHYSICS_PARAMS['E'], PHYSICS_PARAMS['rho'], PHYSICS_PARAMS['gamma'], duration_seconds

        if N_I == 0 or lambda_rate == 0: return 0.0

        term1 = (rho * N_I * E) / (V * lambda_rate)
        term2 = t - (1 - math.exp(-lambda_rate * t)) / lambda_rate
        n_t = term1 * term2
        P_t = 1 - math.exp(-gamma * n_t)
        return P_t

    def print_node_populations(self):
        hypothetical_duration = 3600
        for node_id in sorted(self.nodes.keys()):
            node = self.nodes[node_id]
            total = node.population['infected'] + node.population['non_infected']
            if total > 0:
                infection_prob = self.calculate_infection_probability(node, hypothetical_duration)
                print(f"  {node.id} ({node.category}): Infected={node.population['infected']}, Non-Infected={node.population['non_infected']}, Total={total}, **Hourly Prob={infection_prob:.4f}**")

    def turn1(self):
        print("\n--- Turn 1: Household to School/Office ---")
        for node in self.nodes.values():
            node.population = {'infected': 0, 'non_infected': 0}
            node.people = {}
        
        destinations = self.work_school_ids
        if not destinations: return

        for person_id in self.person_to_household:
            status = self.person_status[person_id]
            destination_id = random.choice(destinations)
            self.person_location[person_id] = destination_id
            self.nodes[destination_id].population[status] += 1
            self.nodes[destination_id].people[person_id] = status
        
        print("\n  State after T1:")
        self.print_node_populations()

    def turn2(self):
        print("\n--- Turn 2: Any to Any ---")
        for node in self.nodes.values():
            node.population = {'infected': 0, 'non_infected': 0}
            node.people = {}

        for person_id in self.person_location:
            status = self.person_status[person_id]
            destination_id = random.choice(self.node_ids)
            self.person_location[person_id] = destination_id
            self.nodes[destination_id].population[status] += 1
            self.nodes[destination_id].people[person_id] = status

        print("\n  State after T2:")
        self.print_node_populations()

    def turn3(self):
        print("\n--- Turn 3: Return to Household ---")
        for node in self.nodes.values():
            node.population = {"infected": 0, "non_infected": 0}
            node.people = {}

        for person_id, household_id in self.person_to_household.items():
            status = self.person_status[person_id]
            self.person_location[person_id] = household_id
            self.nodes[household_id].population[status] += 1
            self.nodes[household_id].people[person_id] = status

        print("\n  State after T3 (All back at households):")
        self.print_node_populations()

    def apply_infection(self, title, duration_seconds):
        print(f"\n--- Applying Physics-Based Infection: {title} (Duration: {duration_seconds/3600:.1f} hours) ---")
        newly_infected_count = 0
        for node_id, node in self.nodes.items():
            if node.population['non_infected'] == 0 or node.population['infected'] == 0: continue
            
            infection_prob = self.calculate_infection_probability(node, duration_seconds)
            if infection_prob == 0.0: continue

            non_infected_people = [pid for pid, status in node.people.items() if status == 'non_infected']
            newly_infected_at_node = 0
            for person_id in non_infected_people:
                if random.random() < infection_prob:
                    self.person_status[person_id] = 'infected'
                    newly_infected_at_node += 1
            
            if newly_infected_at_node > 0:
                newly_infected_count += newly_infected_at_node
                print(f"  {node_id} ({node.category}): {newly_infected_at_node} new infections (Prob: {infection_prob:.4f})")

        print(f"Total newly infected in this step: {newly_infected_count}")
        self._recalculate_node_populations()

    def _recalculate_node_populations(self):
        for node in self.nodes.values():
            node.population = {'infected': 0, 'non_infected': 0}
            node.people = {}
        for person_id, location_id in self.person_location.items():
            status = self.person_status[person_id]
            node = self.nodes[location_id]
            node.population[status] += 1
            node.people[person_id] = status

    def run_simulation(self, days):
        print("\n--- Initial State (Day 0, T0: All at Household) ---")
        self.print_node_populations()
        self._record_history(0)

        duration_t1, duration_t2, duration_t3 = 8 * 3600, 4 * 3600, 12 * 3600

        for day in range(1, days + 1):
            print(f"\n==================== DAY {day} ====================")
            self.turn1()
            self.apply_infection(f"Day {day}, After Turn 1", duration_t1)
            self.turn2()
            self.apply_infection(f"Day {day}, After Turn 2", duration_t2)
            self.turn3()
            self.apply_infection(f"Day {day}, After Turn 3", duration_t3)
            print(f"\n--- End of Day {day} State (All at Household) ---")
            self.print_node_populations()
            self._record_history(day)

    def _record_history(self, day):
        total_infected = sum(1 for status in self.person_status.values() if status == 'infected')
        self.simulation_history.append({'day': day, 'total_infected': total_infected})

if __name__ == "__main__":
    sim = GraphSimulation(CATEGORY_COUNTS, TOTAL_POPULATION, INITIAL_INFECTED_PERCENTAGE)
    sim.run_simulation(SIMULATION_DAYS)
