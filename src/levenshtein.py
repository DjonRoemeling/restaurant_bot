import Levenshtein
from restaurant_loader import load_restaurant_info

DATA_PATH = "data/restaurant_info_extended.csv"

def levensthein_distance(word, data):           
    #Checks if a typo has occured, can be used for dialog to check if the correction matches user wants. 
    closest_match = min(data, key=lambda x: Levenshtein.distance(word, x))
    if Levenshtein.distance(word, closest_match) == 0:
        perfect_match = True
    else:
        perfect_match = False
        if Levenshtein.distance(word, closest_match) > len(word)/3:  #Make it so short words dont get to easily changed like the to thai and want to west        
            closest_match = None    
                
    
    #return the correct version of the word and if there was a typo
    return closest_match, perfect_match
    
if __name__ == "__main__":
    price_ranges, food_types, areas, restaurant_info = load_restaurant_info(DATA_PATH)
    leven_data = price_ranges + food_types + areas
    print(levensthein_distance("spenish", leven_data))