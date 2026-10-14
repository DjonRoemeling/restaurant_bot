import csv

DATA_PATH = "data/restaurant_info_extended.csv"

#Loads all the data from the restaurant file
def load_restaurant_info(path):
    areas = []
    price_ranges = []
    food_types = []
    restaurant_info = []
    with open(path, 'r') as f:
        restaurants = csv.reader(f)
        for row in restaurants:
            if len(restaurant_info) < 1:
                restaurant_info = row[4:7]
            else:
                price_ranges.append(row[1])
                areas.append(row[2])
                food_types.append(row[3])
                
        #Remove duplicates and emtpy data fields
        price_ranges = list({price.strip() for price in price_ranges if price.strip()})
        food_types = list({food.strip() for food in food_types if food.strip()})
        areas = list({area.strip() for area in areas if area.strip()})       
        
        return price_ranges, food_types, areas, restaurant_info
    
if __name__ == "__main__":
    print(load_restaurant_info(DATA_PATH))