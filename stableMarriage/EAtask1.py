from matching.games import StableMarriage
from matching.games import HospitalResident

import random
import sys


def create_pairs(men_prefs, women_prefs, num_pairs):
    paired_men = set()
    paired_women = set()
    pairs = []

    women_list = list(women_prefs.keys())

    while len(pairs) < num_pairs and len(paired_women) < len(women_list):
        woman = random.choice(women_list)
        if woman in paired_women:
            continue

        possible_men = women_prefs[woman]
        random.shuffle(possible_men)
        pair_made = False

        for man in possible_men:
            if man in paired_men:
                continue
            if woman in men_prefs.get(man, []):
                pairs.append((woman, man))
                paired_men.add(man)
                paired_women.add(woman)
                pair_made = True
                break

        if not pair_made:
            # If no pair is made for this iteration, woman stays unpaired this round
            continue

    return pairs



def generate_generation(pairings_count, pairs_in_pairings):
    generation = []
    for _ in range(pairings_count):
        generation.append(create_pairs(pairs_in_pairings))
    
    return generation

def compute_egalitarian(men_prefs, women_prefs, pairing):
    egalitarian_score = 0
    x = []

    for pair in pairing:
        man, woman = pair[0], pair[1]
        man_position = women_prefs[woman]
    pass

def evaluate_pairing(men_prefs, women_prefs, pairing):
    egalitarian_value = compute_egalitarian(men_prefs, women_prefs, pairing)

    pass

def compute():
    pairings_in_generation = 50
    pairs_in_pairings = 50

    generate_generation(pairings_in_generation, pairs_in_pairings)
    pass

# create many parovanie
# evalute parovania
# cut off bad parovania 
# make new parovania



def is_blocking_pair(man, woman, couples, male_preferences, female_preferences):
    """ Check if (man, woman) is a blocking pair. """
    current_partner_man = couples[man]
    current_partner_woman = next(key for key, value in couples.items() if value == woman)

    # Check if man prefers woman over his current partner and woman prefers man over her current partner
    return male_preferences[man].index(woman) < male_preferences[man].index(current_partner_man) and \
            female_preferences[woman].index(man) < female_preferences[woman].index(current_partner_woman)



def parse_preferences(file_path):
    with open(file_path, 'r') as file:
        lines = file.read().splitlines()

    men_prefs_in = {}
    women_prefs_in = {}
    for line in lines:
        parts = line.split(':')
        entity, prefs = parts[0].strip(), parts[1].strip().split()
        if entity.startswith('m'):
            men_prefs_in[entity[1:]] = prefs
        else:
            women_prefs_in[entity[1:]] = prefs

    return men_prefs_in, women_prefs_in


#men_prefs, women_prefs = parse_preferences('./data.txt')
men_prefs, women_prefs = parse_preferences('./test.txt')
# men_prefs1, women_prefs1 = parse_preferences('./dataSMI.txt')


#print(create_pairs(men_prefs, women_prefs, 50))
#print(type(men_prefs))
# print(women_prefs)

def clean_and_flatten_preferences(men_prefs, women_prefs):
    def clean_prefs(prefs):
        clean_list = []
        for item in prefs:
            # Flatten the list if it's nested and remove '-' prefixed items
            if '[' in item:
                # Extract items within brackets and split by spaces
                nested_items = item.strip("[]").split()
                clean_list.extend([x for x in nested_items if not x.startswith('-')])
            elif not item.startswith('-'):
                clean_list.append(item.strip("[]"))
        return clean_list

    # Apply cleaning to men's and women's preferences
    cleaned_men_prefs = {k: clean_prefs(v) for k, v in men_prefs.items()}
    cleaned_women_prefs = {k: clean_prefs(v) for k, v in women_prefs.items()}

    return cleaned_men_prefs, cleaned_women_prefs

print(clean_and_flatten_preferences(men_prefs, women_prefs))



def gale_shapley(men_prefs, women_prefs):
    sys.setrecursionlimit(5000)

    capacities = {woman: 1 for woman in women_prefs.keys()}
    game = HospitalResident.create_from_dictionaries(men_prefs, women_prefs, capacities)
    return game.solve()


#print(gale_shapley(men_prefs, women_prefs))


def initialize_population(men_prefs, women_prefs):
    # Parse the preference strings into lists of integers
    men_prefs_parsed = {man: [parse_preferences(pref) for pref in prefs] for man, prefs in men_prefs.items()}
    women_prefs_parsed = {woman: [parse_preferences(pref) for pref in prefs] for woman, prefs in women_prefs.items()}

    # Create list of all men and shuffle for random pairing
    all_men = list(men_prefs_parsed.keys())
    random.shuffle(all_men)

    # Initialize a dictionary to store the pairings
    pairings = {}

    # Iterate over each woman to find a match
    for woman, prefs in women_prefs_parsed.items():
        for pref in prefs:
            if isinstance(pref, list):
                # Randomly choose from equally preferred men, making sure they are not already paired
                possible_matches = [man for man in pref if man in all_men]
                if possible_matches:
                    chosen_man = random.choice(possible_matches)
                    pairings[woman] = chosen_man
                    all_men.remove(chosen_man)
                    break
            elif (pref > 0) and (pref in all_men):
                # If the preference is positive and the man is available, pair them
                pairings[woman] = pref
                all_men.remove(pref)
                break
            # If pref is negative or man is not available, continue to next preference

    # Note: At this point, some men might remain unpaired if they were undesired by all women
    return pairings




# Generate a single matching
#initial_matching = initialize_population(men_prefs, women_prefs)

# To generate a population, call initialize_population multiple times
#population_size = 10
#population = [initialize_population(men_prefs, women_prefs) for _ in range(population_size)]


def is_strongly_stable(men_preferences, women_preferences, pairings):
    # Check for strong stability. If any individual can improve their situation (even if their new partner
    # is indifferent or the new partner is currently unmatched), the matching is not strongly stable.

    # Check for potential blocks among matched pairs
    for man, woman in pairings.items():
        for other_woman in men_preferences[man]:
            # Check if man prefers other_woman and other_woman is either not matched or prefers man over her current partner
            if man_prefers(men_preferences, man, other_woman, woman) and woman_prefers(women_preferences, other_woman, man, pairings):
                return False  # This pair (man, other_woman) is a blocking pair

        for other_man, other_woman in pairings.items():
            if other_woman == woman:
                continue  # Skip checking the current pair
            # Check if woman prefers other_man and other_man prefers woman over his current partner
            if woman_prefers(women_preferences, woman, other_man, man) and man_prefers(men_preferences, other_man, woman, other_woman):
                return False  # This pair (other_man, woman) is a blocking pair

    # Check for potential blocks with unmatched individuals
    unmatched_women = set(women_preferences.keys()) - set(pairings.values())
    for unmatched_woman in unmatched_women:
        for man in men_preferences.keys():
            if woman_prefers(women_preferences, unmatched_woman, man, pairings.get(man, None)):
                return False  # This pair (man, unmatched_woman) is a blocking pair

    # If no blocking pairs are found, the matching is strongly stable.
    return True


def man_prefers(men_preferences, man, other_woman, current_woman):
    # Check if other_woman is a valid option
    if other_woman == '-':
        return False

    # Get the preference list and indexes for comparison
    man_pref_list = men_preferences[man]
    current_index = man_pref_list.index(current_woman) if current_woman in man_pref_list else float('inf')
    other_index = man_pref_list.index(other_woman)

    # Handle equal preference
    for group in man_pref_list:
        if isinstance(group, list) and current_woman in group and other_woman in group:
            return False  # They are equally preferred

    return other_index < current_index


def woman_prefers(women_preferences, woman, man, current_man):
    # Check if man is a valid option
    if man == '-':
        return False

    # Get the preference list and indexes for comparison
    woman_pref_list = women_preferences[woman]
    current_index = woman_pref_list.index(current_man) if current_man in woman_pref_list else float('inf')
    new_index = woman_pref_list.index(man)

    # Handle equal preference
    for group in woman_pref_list:
        if isinstance(group, list) and current_man in group and man in group:
            return False  # They are equally preferred

    return new_index < current_index


def calculate_fitness(pairings, men_preferences, women_preferences):
    total_happiness = 0
    total_egalitarian_cost = 0

    # Iterate over all pairings to calculate happiness and egalitarian cost
    for man, woman in pairings.items():
        # Calculate positions (add 1 because positions start at 1, not 0)
        man_happiness = men_preferences[man].index(woman) + 1
        woman_happiness = women_preferences[woman].index(man) + 1

        # Calculate happiness for the pairing
        pair_happiness = man_happiness + woman_happiness

        # Calculate egalitarian cost for the pairing
        egalitarian_cost = abs(man_happiness - woman_happiness)

        # Add to total happiness and egalitarian cost
        total_happiness += pair_happiness
        total_egalitarian_cost += egalitarian_cost

    # The fitness score is the sum of all happiness scores plus the sum of all egalitarian costs
    fitness = total_happiness + total_egalitarian_cost

    return fitness, total_happiness, total_egalitarian_cost


#print(initialize_population(men_prefs, women_prefs))
