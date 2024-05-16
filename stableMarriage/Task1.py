#!/usr/bin/env python
# coding: utf-8

# In[25]:


import random
import os
import multiprocessing
from multiprocessing import Pool
from matching.games import HospitalResident
from functools import cache
import cProfile
import re
import logging

print(multiprocessing.cpu_count())

print(len(os.sched_getaffinity(0)))

logger = logging.getLogger(__name__)
# In[11]:


def parse_preferences(file_path):
    with open(file_path, 'r') as file:
        lines = file.read().splitlines()

    men_prefs = {}
    women_prefs = {}
    for line in lines:
        parts = line.split(':')
        entity, prefs = parts[0].strip(), parts[1].strip().split()
        if entity.startswith('m'):
            men_prefs[entity[1:]] = prefs
        else:
            women_prefs[entity[1:]] = prefs
            
    return men_prefs, women_prefs

men_prefs, women_prefs = parse_preferences('./data.txt')
men_prefs1, women_prefs1 = parse_preferences('./dataSMI.txt')

#print(men_prefs)
def gale_shapley(engagers, receivers):
    # engagers and receivers should be dictionaries with keys as names and values as lists of preferences
    unmatched = list(engagers.keys())  # All engagers start unmatched
    proposals = {name: [] for name in engagers}  # Keep track of whom each engager has proposed to
    matches = {name: None for name in receivers}  # Start with no receivers matched

    while unmatched:
        for engager in unmatched[:]:  # Iterate over a snapshot of the list
            engager_prefs = engagers[engager]
            for receiver in engager_prefs:
                if receiver not in proposals[engager]:  # Only propose if not already proposed to this receiver
                    proposals[engager].append(receiver)
                    if matches[receiver] is None:  # Receiver is unmatched
                        matches[receiver] = engager
                        unmatched.remove(engager)
                        break
                    else:  # Receiver is currently matched, check preferences
                        current_match = matches[receiver]
                        receiver_prefs = receivers[receiver]
                        # Check if the receiver prefers the new proposal to the current match
                        if receiver_prefs.index(engager) < receiver_prefs.index(current_match):
                            unmatched.append(current_match)  # The old match becomes unmatched
                            matches[receiver] = engager  # The new match is established
                            unmatched.remove(engager)
                            break
            else:
                # If we exit the inner loop without breaking, engager remains unmatched
                # Add a safety exit condition in case a receiver not in engager's list is matched
                if all(receiver in proposals[engager] for receiver in engager_prefs):
                    unmatched.remove(engager)

    return matches

def gale_shapley_lib(men_prefs, women_prefs):
    capacities = {r: 1 for r in women_prefs.keys()}
    game = HospitalResident.create_from_dictionaries(men_prefs,women_prefs,capacities)
    rslt = game.solve(optimal="resident")
    print(rslt)
    return None 



# In[12]:

def create_chromosome_repeat(men_preferences, women_preferences):
    men = list(men_preferences.keys())
    women = list(women_preferences.keys())
    matches = []
    chosen_women = set()

    for man in men:
        available_women = [w for w in men_preferences[man] if w not in chosen_women]
        if available_women:
            woman = random.choice(available_women)
            matches.append((man, woman))
            chosen_women.add(woman)
    return matches

def create_chromosome(men_preferences, women_preferences):

    chromosome = create_chromosome_repeat(men_preferences, women_preferences)
    stable, _ = is_stable(chromosome, men_preferences, women_preferences)

    while not stable:
        chromosome = create_chromosome_repeat(men_preferences, women_preferences )
        stable, _ = is_stable(chromosome, men_preferences, women_preferences)
    print("Hit stable")
    return chromosome


# In[13]:


def is_stable(chromosome, men_preferences, women_preferences):
    chromosome = chromosome.items()
    def prefers(new, current, preferences):
        # Return True if the individual prefers the new partner over the current partner
        return preferences.index(new) < preferences.index(current)
    
    # Extract the current matches from the chromosome
    man_to_woman = {man: woman for man, woman in chromosome}
    woman_to_man = {woman: man for man, woman in chromosome}
    
    blocking_pairs = 0
    
    # Check each man and woman to see if they form a blocking pair
    for man, woman in chromosome:
        man_prefs = men_preferences[man]
        woman_prefs = women_preferences[woman]
        
        # Check if there is any woman in man's preference list that he prefers more than his current match
        for preferred_woman in man_prefs:
            if preferred_woman == woman:
                break  # He prefers his current match the most, no blocking pair possible beyond this point
            
            preferred_woman_current_man = woman_to_man[preferred_woman]
            # Check if the preferred woman prefers this man over her current match
            if prefers(man, preferred_woman_current_man, women_preferences[preferred_woman]):
                blocking_pairs += 1
                break
        
        # Check if there is any man in woman's preference list that she prefers more than her current match
        for preferred_man in woman_prefs:
            if preferred_man == man:
                break  # She prefers her current match the most, no blocking pair possible beyond this point

            if preferred_man in man_to_woman:
                preferred_man_current_woman = man_to_woman[preferred_man]
                # Check if the preferred man prefers this woman over his current match
                if prefers(woman, preferred_man_current_woman, men_preferences[preferred_man]):
                    blocking_pairs += 1
                    break
    
    # The chromosome is stable if there are no blocking pairs
    is_stable = blocking_pairs == 0
    
    return is_stable, blocking_pairs


# In[14]:


def calculate_happiness_cost(engagements, men_prefs, women_prefs):
    sum = 0
    for man, woman in engagements.items():
        try:
            if woman in men_prefs[man]:
                sum += men_prefs[man].index(woman)
            if man in women_prefs[woman]:
                sum += women_prefs[woman].index(man)
        except KeyError:
            continue
    return sum

def calculate_egalitarian_cost(engagements, men_prefs, women_prefs):
    sum = 0
    for man, woman in engagements.items():
        try:
            if woman in men_prefs[man] and \
               man in women_prefs[woman]:
                sum += abs(men_prefs[man].index(woman) - women_prefs[woman].index(man))
        except KeyError:
            continue
    return sum

def calculate_stability(engagements, men_prefs, women_prefs):
    is_chromosome_stable, blocking_pairs_count = is_stable(engagements, men_prefs, women_prefs) 
    return blocking_pairs_count

def calculate_fitness(engagements, men_prefs, women_prefs):
    happiness_cost = calculate_happiness_cost(engagements, men_prefs, women_prefs)
    egalitarian_cost = calculate_egalitarian_cost(engagements, men_prefs, women_prefs)
    #stability = calculate_stability(engagements, men_prefs, women_prefs)
    
    # Combine the costs into a fitness score (you may want to weigh these differently)
    fitness = egalitarian_cost + happiness_cost
    return fitness


# In[15]:


def one_point_crossover(parent1, parent2):
    # Convert the engagements to lists for easy crossover
    men1, women1 = zip(*parent1.items())
    men2, women2 = zip(*parent2.items())

    crossover_point = random.randint(1, len(men1) - 2)
    new_men = men1[:crossover_point] + men2[crossover_point:]
    new_women = women1[:crossover_point] + women2[crossover_point:]

    # Remove duplicates to maintain valid engagements
    engagements = {}
    for m, w in zip(new_men, new_women):
        if w not in engagements.values():
            engagements[m] = w
            
    return engagements


# In[16]:


def swap_mutation(individual):
    men = list(individual.keys())
    m1, m2 = random.sample(men, 2)
    individual[m1], individual[m2] = individual[m2], individual[m1]
    return individual

def swap_keys_with_values(dictionary):
    swapped_dictionary = {}
    for key in dictionary.keys():
        swapped_dictionary[dictionary[key]] = key
    return swapped_dictionary

# In[21]:
def create_initial_chromosomes(men_prefs, women_prefs):
    male_side = gale_shapley(men_prefs, women_prefs)
    female_side = swap_keys_with_values(gale_shapley(women_prefs, men_prefs))

    return male_side, female_side

def get_more_preffered_partner(choice1, choice2, preference_list:list):
    if preference_list.index(choice1) < preference_list.index(choice2):
        return choice1
    return choice2

def get_less_preffered_partner(choice1, choice2, preference_list:list):
    if preference_list.index(choice1) > preference_list.index(choice2):
        return choice1
    return choice2

def swap_partners(chromosome, first_man, second_man, men_prefs):
    if first_man == second_man:
        raise ValueError("Both males are the same individual")

    new_chromosome = dict(chromosome)
    # A:1, C:4
    first_woman = chromosome[first_man]
    second_woman = chromosome[second_man]

    # They cannot be paired together
    if (second_woman not in men_prefs[first_man]) or \
       (first_woman not in men_prefs[second_man]):
       raise ValueError("Invalid pair")
    
    new_chromosome[first_man] = get_more_preffered_partner(first_woman, second_woman, men_prefs[first_man])    
    new_chromosome[second_man] = get_less_preffered_partner(first_woman, second_woman, men_prefs[second_man])    

    return new_chromosome



def mutate_chromosome(chromosome, men_prefs, women_prefs):
    # A:1 , C:4
    number_of_mutations = random.randint(3,50)

    current_mutations = 0
    while current_mutations <= number_of_mutations:
        try:
            male1, male2 = random.choice(list(chromosome.keys())), random.choice(list(chromosome.keys()))
            chromosome = swap_partners(chromosome, male1, male2, men_prefs)
            current_mutations += 1
        except ValueError as e:
            logger.info(f"{str(e)}")            
            continue
        except KeyError:
            continue
    
    return chromosome



# Modified evolutionary algorithm with parallelization
def evolutionary_algorithm(men_prefs, women_prefs, pop_size, generations):

    initial_chromosomes = create_initial_chromosomes(men_prefs, women_prefs)
    
    population = [initial_chromosomes[0]]
    for i in range(pop_size):
        population.append(mutate_chromosome(random.choice(population), men_prefs, women_prefs))
    
    best_fit = None
    best_solution = None

    for _ in range(generations):
        fitness_scores = [(calculate_fitness(chromosome, men_prefs, women_prefs), chromosome) for chromosome in population]
        fitness_scores = sorted(fitness_scores, key=lambda x: x[0])
        
        parents = list(map(lambda x: x[1], fitness_scores))
        fitness_scores = list(map(lambda x: x[0], fitness_scores))

        new_population = parents[:len(parents) // 2]
        for i in range(pop_size//2):
            new_population.append(mutate_chromosome(random.choice(new_population), men_prefs, women_prefs))
        new_population = new_population[:100]
        assert(len(new_population) == pop_size)
        
        # Check if we have a new best solution

        population = new_population

        if best_fit is None or fitness_scores[0] > best_fit:
            best_fit = fitness_scores[0]
            best_solution = new_population[0]
            
    return best_solution, best_fit


# In[26]:

def write_solution_to_file(result: dict):
    with open("solution.txt", "w") as file:
        for man, woman in result.items():
            if woman in ["95", "96", "97", "98", "99"]:
                continue
            file.write(f"m{man} w{woman}\n")
    print (f"Solution successfully written to {file.name}")

def main():
    best_solution, best_fit = evolutionary_algorithm(men_prefs, women_prefs, pop_size=100, generations=100)
    print("Best Solution:")
    for man, woman in best_solution.items():
        print(f"{man} is matched with {woman}")
    print(f"Best Fitness: {best_fit}")
    write_solution_to_file(best_solution)

# Now, we can call the evolutionary algorithm with the correct path to your data file
if __name__ == "__main__":
    #main()
    #cProfile.run('re.compile("main()")')

    original = gale_shapley(men_prefs, women_prefs)
    stable = is_stable(original, men_prefs, women_prefs)
    print("Solution is stable:", stable)
    write_solution_to_file(gale_shapley(men_prefs, women_prefs))
    #print(gale_shapley(men_prefs1, women_prefs1))


# %%
