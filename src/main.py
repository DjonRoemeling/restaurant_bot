import joblib
import csv
import streamlit as st
from levenshtein import levensthein_distance
from restaurant_loader import load_restaurant_info
from reasoning import extract_requirement, filter_by_requirement, explain

DATA_PATH = "data/restaurant_info_extended.csv"
SHOW_REASONING = True #show or hide the inference chain behind a recommendation.
restaurants = [] 
restaurant_index = 0 #increase this index to get the next restaurant recommendation if the user wants a different one
preferred_area = None
preferred_food_type = None
preferred_price_range = None
active_requirement = None #the additional requirement the user asked for
price_ranges, food_types, areas, restaurant_info = load_restaurant_info(DATA_PATH)
leven_data = price_ranges + food_types + areas


def check_restaurant(path): 
    good_restaurants = []
    with open(path, 'r') as f:
        restaurants = csv.DictReader(f)
        for restaurant in restaurants:
            if (restaurant["area"] == preferred_area or preferred_area is None) and (restaurant["food"] == preferred_food_type or preferred_food_type is None) and (restaurant["pricerange"] == preferred_price_range or preferred_price_range is None):
                good_restaurants.append(restaurant)
    return good_restaurants

def ask_additional_requirement(candidates):
    #asks for extra requirement and filters candidate restaurants
    answer = input("Do you have any additional requirements? You can ask for somewhere touristic, romantic, suitable for children, or with assigned seating. ").lower()

    requirement = extract_requirement(answer)
    if requirement is None:
        return candidates, None

    consequent, wanted = requirement
    filtered = filter_by_requirement(candidates, consequent, wanted)

    if len(filtered) == 0:
        print("None of the restaurants matching your preferences meet that requirement, so I will leave it out.")
        return candidates, None

    return filtered, requirement

def reasoning_line(restaurant):
    #sentence justifying recommendation
    if not SHOW_REASONING or active_requirement is None:
        return ""
    return "\n" + explain(restaurant, active_requirement[0])

#Looks what is still unknown about prefrences and asks for them directly
def ask_next_question(mode):
    if mode == "eager" and (preferred_area is not None or preferred_food_type is not None or preferred_price_range is not None):
        return None
    if preferred_area is None:
        return "Would you like to eat in the west, north, south, centre, or east Cambridge area? "
    elif preferred_food_type is None:
        return "What type of food would you like? For example, British, Italian, etc. "
    elif preferred_price_range is None:
        return "Are you looking for moderate, expensive, or cheap prices? "
    else:
        return None

#Tries to match the input to important wordt from the data
def keyword_matching(user_input, levensthein=True):   
    global preferred_area 
    global preferred_food_type
    global preferred_price_range
    
    if levensthein == True:
        words = user_input.split()     
        matched = False
        
        for word in words:  
            match, perfect = levensthein_distance(word, leven_data)
            if not perfect and match != None:
                yesno = st.write (f"Was {word} supposed to be {match}? Please answer with 'yes' or 'no'. ")
                if "yes" not in yesno:
                    matched = False
                    match = word #Do this so after the 'no' it doesn't still match it.
                
            if match in areas:
                preferred_area = match
                matched = True            
            
            if match in food_types:           
                preferred_food_type = match
                matched = True

            if match in price_ranges:
                preferred_price_range = match
                matched = True
               
        return matched
    
    else:    
        area_match = next((area for area in areas if area in user_input), None)
        food_match = next((food for food in food_types if food in user_input), None)
        price_match = next((match for match in price_ranges if match in user_input), None)
        if area_match is not None:
            preferred_area = area_match

        if food_match is not None:
            preferred_food_type = food_match

        if price_match is not None:
            preferred_price_range = price_match
    
        if area_match is not None or food_match is not None or price_match is not None:
            return True
        return False
    
                
def caca(user_input):

    model = joblib.load("data/mlp.pkl")
    vec= joblib.load("data/vectorizer.pkl")
    mode="patient"
    utterance = model.predict(vec.transform([user_input]))
    if utterance == "hello":
        print("Hello!")
        keyword_matching(user_input, True) #This makes it so that even if the utterance is hello, the system will still check if the user has specified any preferences in their greeting.
        user_input = ask_next_question(mode)
        if user_input is None and len(restaurants) > 0:
            return (f"We have the preferred restaurant for you: {restaurants[restaurant_index]['restaurantname']}{reasoning_line(restaurants[restaurant_index])}\nIf you would like a different restaurant recommendation, please type 'next'. If you would like more information about the restaurant, please specify what you need. ").lower()
            #If the user says hello after the system has already recommended a restaurant, the system will ask if they want a different recommendation or more information about the restaurant.
        
    elif utterance == "inform":
        matched = keyword_matching(user_input)
        if matched == False:
            st.write("Sorry, I didn't understand that")
        restaurants = []
        return ask_next_question(mode)
         #This resets the restaurant list so that if the user changes their preferences, the system will search for new restaurants matching the updated preferences.
        active_requirement = None #The additional requirement belongs to the old candidate list, so it is dropped too.
                        
    elif utterance == "request":                
        if len(restaurants) == 0: #If no restaurant is picked there is no info to give
            st.write("We have not picked any restaurants yet, please answer the following questions.")
            return ask_next_question(mode)
        else:
            request_match = [r for r in restaurant_info if r in user_input]
            if len(request_match) > 0:   
                for request in request_match:                        
                    if restaurants[restaurant_index][request] != "":
                        return f"The {request} of the restaurant {restaurants[restaurant_index]['restaurantname']} is: {restaurants[restaurant_index][request]}"
                    else:
                        return f"Sorry, we don't have the {request} of the restaurant {restaurants[restaurant_index]['restaurantname']}."
                return "If you would like more information about the restaurant, please specify what you need. "
            else:
                return "Sorry, I didn't understand that, please ask for the phone number with 'phone number', address with 'address', or postcode with 'postcode' of the restaurant. "
    
    elif utterance == "reqalts":
        restaurant_index += 1                
        if restaurant_index >= len(restaurants):
            restaurant_index -= 1
            user_input = "Sorry, we don't have any more restaurants matching your preferences. Would you like to start over and try again? If so, please type 'start again'. "
             #This makes sure that the user can still request information about the previous restaurant.
            if "start again" in user_input:
                restaurant_index = 0
                preferred_area = None
                preferred_food_type = None
                preferred_price_range = None
                restaurants = []
                return ask_next_question(mode)                  
        else:
            if restaurant_index == (len(restaurants)-1):
                return f"Here is a restaurant you might like: {restaurants[restaurant_index]['restaurantname']}{reasoning_line(restaurants[restaurant_index])}\nIf you would like a different restaurant recommendation, please type 'next'. If you would like more information about the restaurant, please specify what you need. "
            else:
                return f"Here is a restaurant you might like: {restaurants[restaurant_index]['restaurantname']}{reasoning_line(restaurants[restaurant_index])}\nIf you would like more information about the restaurant, please specify what you need. "

            
    elif utterance == "bye":
        return "Goodbye!"
        
    
    else:
        st.write("Sorry, I didn't understand that")        
        user_input = ask_next_question(mode)         
        if user_input is None:
            return "Please try again. "
            
    #Checks if it has all the info and if a restaurant still needs to be picked
    if user_input is None and len(restaurants) == 0:
        restaurants = check_restaurant(DATA_PATH)
        if len(restaurants) == 0:
            user_input = "Sorry, we couldn't find any restaurants matching your preferences. Would you like to start over and try again? If so, please type 'start again'. "
            if "start again" in user_input:
                restaurant_index = 0
                preferred_area = None
                preferred_food_type = None
                preferred_price_range = None
                restaurants = []
                user_input = ask_next_question(mode)
        else:
            restaurants, active_requirement = ask_additional_requirement(restaurants) #Reasoning step
            restaurant_index = 0 #filtering changes the list, so the index has to start again.
            if len(restaurants) > 1:
                
                return f"Here is a restaurant you might like: {restaurants[restaurant_index]['restaurantname']}{reasoning_line(restaurants[restaurant_index])}. If you would like a different restaurant recommendation, please type 'next'. If you would like more information about the restaurant, please specify what you need. "
            else:
                return f"Here is a restaurant you might like: {restaurants[restaurant_index]['restaurantname']}{reasoning_line(restaurants[restaurant_index])}. If you would like more information about the restaurant, please specify what you need. "
            