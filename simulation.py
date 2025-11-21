# simulation.py
import random
import math
from collections import defaultdict

class Person:
    """Represents a single individual agent in the simulation."""
    def __init__(self, person_id, neighborhood_id):
        self.id = person_id
        self.neighborhood_id = neighborhood_id
        
        self.age_group = None  # '1-18', '18-64', '65+'
        self.employment = None # 'teacher', 'clerk', 'office_worker', etc.
        
        # S-E-I-A-R Disease Model
        self.disease_state = 'susceptible' # susceptible, exposed, infectious, asymptomatic, removed, dead
        self.days_in_state = 0
        self.is_vaccinated = False
        self.is_quarantined = False
    
        self.is_detected = False # Has the person been detected as sick?

        self.home_id = None
        self.work_id = None
        self.location_id = None

class Node:
    """A generic class for any location (shop, park, school, office, etc.)."""
    def __init__(self, node_id, category, neighborhood_id=None):
        self.id = node_id
        self.category = category
        self.neighborhood_id = neighborhood_id
        self.people_ids = set() # Set of person_ids currently at this node


class Simulation:
    """The main class that orchestrates the entire simulation."""
    
    def __init__(self, config):
        self.config = config
        self.day = 0
        self.people = {}
        self.nodes = {}
        self.neighborhood_definitions = {} # {nid: {'nodes': [], 'people': []}}
        self.public_transport_node = Node('public_transport', 'transport')
        self.history = []
        self.log = [] # A list to store turn-by-turn explanations
        self._log_message("--- Initializing Simulation World ---")

        self._create_world()

    def _log_message(self, message):
        """Adds a formatted message to the simulation log."""
        self.log.append(message)


    def _create_world(self):
        print("--- Initializing Simulation World ---")
        
        # 1. Calculate world structure
        total_pop = self.config['total_population']
        num_neighborhoods = math.ceil(total_pop / (10000 / 15)) # Approx. 15 neighborhoods per 10k people
        pop_per_neighborhood = total_pop // num_neighborhoods
        
        # 2. Create People with demographics
        self._create_people(total_pop, num_neighborhoods, pop_per_neighborhood)
        
        # 3. Create Nodes (households, workplaces, etc.)
        self._create_nodes(total_pop)
        
        # 4. Assign people to homes and workplaces
        self._assign_people_to_homes_and_work()
        
        # 5. Set initial disease, vaccination, and quarantine states
        self._set_initial_states()
        
        print("--- Initialization Complete ---")

    def _create_people(self, total_pop, num_neighborhoods, pop_per_neighborhood):
        age_dist = {'1-18': 0.1, '18-64': 0.6, '65+': 0.3} # Default 'medium'
        if self.config['age_of_population'] == 'young': age_dist = {'1-18': 0.3, '18-64': 0.6, '65+': 0.1}
        if self.config['age_of_population'] == 'old': age_dist = {'1-18': 0.1, '18-64': 0.6, '65+': 0.3}
        
        employment_dist = {'teacher': 0.2, 'clerk': 0.1, 'food_industry': 0.1, 'office_worker': 0.3, 'healthcare_worker': 0.1, 'from_home': 0.2}

        for i in range(total_pop):
            person_id = f"P{i}"
            nid = f"N{i // pop_per_neighborhood + 1}"
            p = Person(person_id, nid)
            
            p.age_group = random.choices(list(age_dist.keys()), weights=list(age_dist.values()), k=1)[0]
            
            if p.age_group == '18-64':
                p.employment = random.choices(list(employment_dist.keys()), weights=list(employment_dist.values()), k=1)[0]
            elif p.age_group == '1-18':
                p.employment = 'student'
            else: # 65+
                p.employment = 'retired'
            
            self.people[person_id] = p
            if nid not in self.neighborhood_definitions: self.neighborhood_definitions[nid] = {'nodes': [], 'people': []}
            self.neighborhood_definitions[nid]['people'].append(person_id)

    def _create_nodes(self, total_pop):
        # Distribution per 10,000 people
        dist = {'h': 8000, 'sh': 15, 'p': 2, 's': 4, 'r': 45, 'H': 1, 'o': 10, 'st': 1, 'pa': 10, 'c': 5, 't': 5}
        
        for category, count_per_10k in dist.items():
            num_nodes = math.ceil(total_pop / 10000 * count_per_10k)
            is_local = category in ['h', 'sh', 'r'] # Local nodes as per plan
            
            for i in range(num_nodes):
                if is_local:
                    # Distribute local nodes among neighborhoods
                    nid = f"N{i % len(self.neighborhood_definitions) + 1}"
                    node_id = f"{category}{i+1}_{nid}"
                    self.nodes[node_id] = Node(node_id, category, neighborhood_id=nid)
                    self.neighborhood_definitions[nid]['nodes'].append(node_id)
                else: # City-wide node
                    node_id = f"{category}{i+1}"
                    self.nodes[node_id] = Node(node_id, category)

    def _assign_people_to_homes_and_work(self):
        # Assign homes
        all_households = [nid for nid, node in self.nodes.items() if node.category == 'h']
        if not all_households:
            raise ValueError("Cannot assign homes, no household nodes were created. Check node distribution rules.")

        for person in self.people.values():
            # Simple assignment for template, can be improved with family logic
            person.home_id = random.choice(all_households)
            person.location_id = person.home_id
            self.nodes[person.home_id].people_ids.add(person.id)

        # Assign work-
        # We pre-compile lists of possible work nodes to avoid repeated filtering.
        school_nodes = [nid for nid, n in self.nodes.items() if n.category == 's']
        office_nodes = [nid for nid, n in self.nodes.items() if n.category == 'o']
        hospital_nodes = [nid for nid, n in self.nodes.items() if n.category == 'H']
        shop_nodes = [nid for nid, n in self.nodes.items() if n.category == 'sh']
        restaurant_nodes = [nid for nid, n in self.nodes.items() if n.category == 'r']

        for person in self.people.values():
            emp = person.employment
            
            # The .id has been removed from the end of each line.
            if emp == 'student' and school_nodes:
                person.work_id = random.choice(school_nodes)
            elif emp == 'teacher' and school_nodes:
                person.work_id = random.choice(school_nodes)
            elif emp == 'office_worker' and office_nodes:
                person.work_id = random.choice(office_nodes)
            elif emp == 'healthcare_worker' and hospital_nodes:
                person.work_id = random.choice(hospital_nodes)
            elif emp == 'clerk' and shop_nodes:
                person.work_id = random.choice(shop_nodes)
            elif emp == 'food_industry' and restaurant_nodes:
                person.work_id = random.choice(restaurant_nodes)
            elif emp == 'from_home' or emp == 'retired':
                person.work_id = person.home_id
            else:
                # Fallback for people whose workplace doesn't exist (e.g., all shops are closed)
                person.work_id = person.home_id


    def _set_initial_states(self):
        person_ids = list(self.people.keys())
        random.shuffle(person_ids)
        
        num_infected = int(len(person_ids) * self.config['percentage_infected'])
        num_removed = int(len(person_ids) * self.config['percentage_removed'])
        num_vaccinated = int(len(person_ids) * self.config['preventative_measures']['vaccination_percentage'])

        for i, pid in enumerate(person_ids):
            if i < num_infected: self.people[pid].disease_state = 'infectious'
            elif i < num_infected + num_removed: self.people[pid].disease_state = 'removed'
        
        # Apply vaccinations
        susceptible_ids = [pid for pid, p in self.people.items() if p.disease_state == 'susceptible']
        random.shuffle(susceptible_ids)
        for i in range(min(num_vaccinated, len(susceptible_ids))):
            pid = susceptible_ids[i]
            if random.random() < self.config['preventative_measures']['vaccination_effectiveness']:
                self.people[pid].disease_state = 'removed' # Effective vaccination confers immunity
                self.people[pid].is_vaccinated = True

    def run_one_day(self):
        """Executes the main loop for a single simulation day with logging."""
        self.day += 1
        self._log_message(f"\n==================== DAY {self.day} ====================")
        
        self._update_disease_progression()
        self._move_and_infect('work')
        self._move_and_infect('social')
        self._move_and_infect('home')
        self._record_history()


# In simulation.py, replace the existing _move_and_infect and _apply_infection_in_node methods with these.

    def _move_and_infect(self, turn_type):
        """
        Handles movement and infection for a turn, now with dynamic sub-grouping
        for locations like schools, offices, etc.
        """
        self._log_message(f"--- Turn: {turn_type.capitalize()} ---")

        # 1. Clear current locations from all nodes
        for node in self.nodes.values():
            node.people_ids.clear()
        self.public_transport_node.people_ids.clear()

        # 2. Pre-compile destination lists for efficiency
        hospital_nodes = [nid for nid, n in self.nodes.items() if n.category == 'H']
        social_nodes = {cat: [nid for nid, n in self.nodes.items() if n.category == cat] for cat in ['r', 'sh', 'c', 't', 'st', 'pa']}

        # 3. Handle Public Transport (if applicable)
        transport_users = []
        if turn_type == 'work' and self.config['public_transport_on']:
            for person in self.people.values():
                if not person.is_quarantined and person.work_id != person.home_id:
                    work_node = self.nodes.get(person.work_id)
                    if work_node and work_node.neighborhood_id is None:
                        if random.random() < 0.25:
                            transport_users.append(person)
        
        if transport_users:
            self._log_message(f"  {len(transport_users)} people are using public transport.")
            self._apply_infection_in_aggregate_node(self.public_transport_node, transport_users, 1)

        # 4. Determine final destination for every person
        for person in self.people.values():
            destination = person.location_id  # Default to current location

            if person.is_quarantined:
                destination = person.home_id
            elif person.is_detected and hospital_nodes:
                destination = random.choice(hospital_nodes)
            elif turn_type == 'work':
                destination = person.work_id
            elif turn_type == 'social':
                social_dist = {'r': 0.1, 'sh': 0.15, 'c': 0.05, 't': 0.05, 'st': 0.05, 'pa': 0.1, 'home': 0.5}
                allowed_choices = {cat: prob for cat, prob in social_dist.items() if cat == 'home' or self.config['active_nodes'].get(cat, False)}
                
                if not allowed_choices:
                    destination = person.home_id
                else:
                    total_prob = sum(allowed_choices.values())
                    normalized_weights = [p / total_prob for p in allowed_choices.values()]
                    choice = random.choices(list(allowed_choices.keys()), weights=normalized_weights, k=1)[0]
                    
                    if choice == 'home':
                        destination = person.home_id
                    else:
                        possible_nodes = social_nodes.get(choice, [])
                        if possible_nodes:
                            destination = random.choice(possible_nodes)
                        else:
                            destination = person.home_id
            elif turn_type == 'home':
                destination = person.home_id
            
            person.location_id = destination
            if destination in self.nodes:
                self.nodes[destination].people_ids.add(person.id)

        # 5. Log populations and apply infection with dynamic sub-grouping
        duration_map = {'work': 8, 'social': 4, 'home': 12}
        duration_hours = duration_map[turn_type]
        self._log_message(f"Applying infection for {duration_hours} hours...")

        subgroup_categories = self.config.get('subgroup_sizes', {})

        for node_id, node in self.nodes.items():
            if not node.people_ids:
                continue

            # Log the total population of the building/node
            total_pop = len(node.people_ids)
            total_inf = len([pid for pid in node.people_ids if self.people[pid].disease_state in ['infectious', 'asymptomatic']])
            self._log_message(f"  At node {node_id}: {total_pop} people ({total_inf} infectious).")

            # Check if this node needs to be divided into smaller "rooms"
            if node.category in subgroup_categories and total_pop > 0:
                room_size = subgroup_categories[node.category]
                people_at_node = list(node.people_ids)
                random.shuffle(people_at_node)

                self._log_message(f"    -> Dividing into 'rooms' of ~{room_size} people.")
                rooms = [people_at_node[i:i + room_size] for i in range(0, len(people_at_node), room_size)]

                # Apply infection to each room separately
                for i, room_pids in enumerate(rooms):
                    room_as_node = type('TempRoom', (object,), {'people_ids': set(room_pids), 'category': node.category})()
                    newly_exposed = self._apply_infection_in_node(room_as_node, duration_hours)
                    if newly_exposed > 0:
                        self._log_message(f"      - In Room #{i+1}: {newly_exposed} new person(s) exposed.")
            
            # For nodes that are NOT sub-grouped (like a single household), apply infection directly
            elif total_pop > 1:
                self._apply_infection_in_node(node, duration_hours)


    def _apply_infection_in_node(self, node, duration_hours):
        """
        Calculates and applies infection probability in a specific node (or temporary room)
        using the Wells-Riley physics-based model.
        Returns the number of newly exposed people for logging.
        """
        node_people = [self.people[pid] for pid in node.people_ids]
        susceptible = [p for p in node_people if p.disease_state == 'susceptible']
        infectious_people = [p for p in node_people if p.disease_state in ['infectious', 'asymptomatic']]
        
        if not susceptible or not infectious_people:
            return 0 # Return 0 as no new infections occurred

        # --- Wells-Riley Model Implementation ---
        t = duration_hours * 3600.0
        N_I = len(infectious_people)
        
        category_params = self.config['physics_params']['categories'].get(node.category)
        if not category_params: return 0

        V = category_params['V']
        lambda_rate = category_params['lambda']
        
        E = self.config['physics_params']['E']
        rho = self.config['physics_params']['rho']
        gamma = self.config['infectivity']

        if lambda_rate == 0: return 0

        term1 = (rho * N_I * E) / (V * lambda_rate)
        term2 = t - (1 - math.exp(-lambda_rate * t)) / lambda_rate
        n_t = term1 * term2

        if n_t <= 0: return 0
        prob = 1 - math.exp(-gamma * n_t)
        
        # Apply probability and count new infections
        newly_infected_count = 0
        for person in susceptible:
            if random.random() < prob:
                person.disease_state = 'exposed'
                person.days_in_state = 0
                newly_infected_count += 1
        
        # Log the calculation if it was significant
        if newly_infected_count > 0:
            self._log_message(f"      - Infection calc: Prob={prob:.4f}, N_I={N_I}, V={V}, ACH={lambda_rate*3600:.1f} -> {newly_infected_count} exposed.")

        return newly_infected_count


    def _apply_infection_in_aggregate_node(self, agg_node, people_group, duration_hours):
        """
        Applies infection for non-node groups (like public transport)
        using the same physics-based model.
        """
        susceptible = [p for p in people_group if p.disease_state == 'susceptible']
        infectious_people = [p for p in people_group if p.disease_state in ['infectious', 'asymptomatic']]
        
        if not susceptible or not infectious_people:
            return

        t = 3600.0
        N_I = len(infectious_people)
        
        V = 80
        lambda_rate = 15.0 / 3600.0
        
        E = self.config['physics_params']['E']
        rho = self.config['physics_params']['rho']
        gamma = self.config['infectivity']

        if lambda_rate == 0: return

        term1 = (rho * N_I * E) / (V * lambda_rate)
        term2 = t - (1 - math.exp(-lambda_rate * t)) / lambda_rate
        n_t = term1 * term2

        if n_t <= 0: return
        prob = 1 - math.exp(-gamma * n_t)
        
        for person in susceptible:
            if random.random() < prob:
                person.disease_state = 'exposed'
                person.days_in_state = 0


    def _update_disease_progression(self):
        for person in self.people.values():
            person.days_in_state += 1
            
            if person.disease_state == 'exposed' and person.days_in_state > self.config['time_of_incubation']:
                # 50/50 chance of being symptomatic vs asymptomatic for this template
                person.disease_state = 'infectious' if random.random() < 0.5 else 'asymptomatic'
                person.days_in_state = 0
            
            elif person.disease_state in ['infectious', 'asymptomatic'] and person.days_in_state > self.config['time_of_activation']:
                if random.random() < self.config['percentage_of_death']:
                    person.disease_state = 'dead' # A terminal state
                else:
                    person.disease_state = 'removed'
                person.days_in_state = 0

            # Detection logic
            if person.disease_state == 'infectious' and not person.is_detected:
                if random.random() < self.config['detection_of_disease_rate']:
                    person.is_detected = True
                    # Optional: Quarantine logic
                    if self.config['preventative_measures']['quarantine_on_detection']:
                        person.is_quarantined = True

    def _record_history(self):
        counts = defaultdict(int)
        for p in self.people.values():
            counts[p.disease_state] += 1
        self.history.append(counts)

