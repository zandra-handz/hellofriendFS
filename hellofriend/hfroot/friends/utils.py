# Validates addresses

import requests
from django.conf import settings 

api_key = settings.GOOGLE_MAPS_API_KEY

def get_coordinates(address):
    base_url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": address,
        "key": api_key,
    }

    response = requests.get(base_url, params=params)
    data = response.json()

    if data["status"] == "OK":
        location = data["results"][0]["geometry"]["location"]
        return location['lat'], location['lng']
    else:
        print(f"Error: Unable to retrieve coordinates for {address}")
        return None
    

# DistanceClass

import requests
from geopy import distance
from geopy.distance import geodesic


def validate_address(address):
    base_url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": address,
        "key": api_key,
    }

    response = requests.get(base_url, params=params)
    data = response.json()

    if data["status"] == "OK":
        return True
    else:
        return


def calculate_travel_time(address, temporary_destination):
    base_url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": address,
        "destination": temporary_destination,
        "mode": "driving",
        "key": api_key,
    }

    response = requests.get(base_url, params=params)
    data = response.json()

    if data["status"] == "OK":
        route = data["routes"][0]["legs"][0]
        duration = route["duration"]["text"]
        return duration
    else:
        print(f"Error: Unable to retrieve travel time from {address} to {temporary_destination}")
        return None, None


def calculate_distance(origin, destination):
    return distance.distance(origin, destination).miles


class Distance():

    def __init__(self, origin_a, destination=None, radius=5000, search="restaurants", suggested_length=8, perform_search=False, search_only=False, **friend_origins):
        self.api_key = api_key
        self.origin_a = origin_a
        self.friend_origins = friend_origins
        self.destination = destination
        self.midpoint = None
        self.perform_search = perform_search
        self.search_only = search_only
        self.search = search
        self.radius = radius
        self.suggested_length = suggested_length

        if not self.validate_address(origin_a):
            raise ValueError(f"Invalid address: {origin_a}")

        for friend_name, friend_address in friend_origins.items():
            if not self.validate_address(friend_address):
                raise ValueError(f"Invalid address for {friend_name}: {friend_address}")

        if not self.search_only:
            if not self.validate_address(destination):
                raise ValueError(f"Invalid address: {destination}")


    def validate_address(self, address):
        return validate_address(address)

    def get_my_address(self):
        return self.origin_a

    def get_friend_address(self, friend_name):
        return self.friend_origins.get(friend_name, None)

    def add_friend_address(self, friend_name, friend_address):
      if self.validate_address(friend_address):
        self.friend_origins[friend_name] = friend_address
        return True
      return False


    def get_all_friend_info(self):
      friend_info = {}
      for idx, (friend, address) in enumerate(self.friend_origins.items()):
        friend_info[idx] = {
            'friend': friend,
            'address': address,
        }
      return friend_info


    def change_destination(self, address):
        if self.validate_address(address):

            self.destination = address
            return self.destination

        print("Cannot validate new destination.")
        return False


    def change_keyword(self, value=str):
        self.search = value
        return self.search
    

    def change_radius(self, value=int):

        try:
            value = int(value)

            self.radius = value
            return self.radius
        
        except ValueError:
            print("Unsuccessful entry.")
            return False
    

    def change_suggested_length(self, value=int):

        try:
            value = int(value)
            
            if value > 20:
                print("List length not accepted (cannot exceed 20).")
                return False
            self.suggested_length = value
            return self.suggested_length

        except ValueError:
            print("Unsuccesful entry.")
            return False


    def get_coordinates_and_formatted_address(self, address):
        base_url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "address": address,
            "key": self.api_key,
        }

        response = requests.get(base_url, params=params)
        data = response.json()

        if data["status"] == "OK":
            location = data["results"][0]["geometry"]["location"]
            return location['lat'], location['lng'], data['results'][0]['formatted_address']
        else:
            print(f"Error: Unable to retrieve coordinates for {address}")
            return None


    def get_coordinates(self, address):
        base_url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "address": address,
            "key": self.api_key,
        }

        response = requests.get(base_url, params=params)
        data = response.json()

        if data["status"] == "OK":
            location = data["results"][0]["geometry"]["location"]
            return location['lat'], location['lng']
        else:
            print(f"Error: Unable to retrieve coordinates for {address}")
            return None


    def get_directions(self, address, destination):
        base_url = "https://maps.googleapis.com/maps/api/directions/json"
        params = {
            "origin": address,
            "destination": destination,
            "key": self.api_key,
        }

        response = requests.get(base_url, params=params)
        data = response.json()

        if data["status"] == "OK":
            route = data["routes"][0]["legs"][0]
            distance = route["distance"]["text"]
            duration = route["duration"]["text"]
            return distance, duration
        else:
            print(f"Error: Unable to retrieve directions for {address} to {destination}")
            return None, None


    def compare_directions(self, many=False):

        if not self.friend_origins:
            print("No other addresses to compare to.")
            return None

        latitude_a, longitude_a, formatted_address_a = self.get_coordinates_and_formatted_address(self.origin_a)
        latitude_dest, longitude_dest, formatted_add_dest = self.get_coordinates_and_formatted_address(self.destination)

        distances_and_durations = {}

        if latitude_a and latitude_dest:

            distance_a_to_dest, duration_a_to_dest = self.get_directions(formatted_address_a, formatted_add_dest)
            if distance_a_to_dest:
                distances_and_durations["Me"] = {
                    'address': formatted_address_a,
                    'distance': distance_a_to_dest,
                    'duration': duration_a_to_dest
                }

        else:
            return None

        if not many:

            friend_items = list(self.friend_origins.items())
            friend, address = friend_items[0]
            latitude, longitude, formatted_address = self.get_coordinates_and_formatted_address(address)

            distance_b_to_dest, duration_b_to_dest = self.get_directions(formatted_address, formatted_add_dest)

            if distance_b_to_dest:

                distances_and_durations[friend] = {
                    'address': formatted_address,
                    'distance': distance_b_to_dest,
                    'duration': duration_b_to_dest
                }

        else:

            for friend, address in self.friend_origins.items():
                latitude, longitude, formatted_address = self.get_coordinates_and_formatted_address(address)
                distance_b_to_dest, duration_b_to_dest = self.get_directions(formatted_address, formatted_add_dest)

                if distance_b_to_dest:

                    distances_and_durations[friend] = {
                        'address': formatted_address,
                        'distance': distance_b_to_dest,
                        'duration': duration_b_to_dest
                    }

        return distances_and_durations


    def get_midpoint_for_multiple(self):
        if not self.friend_origins:
            return False

        latitude_a, longitude_a = self.get_coordinates(self.origin_a)

        friend_coordinates = [self.get_coordinates(address) for address in self.friend_origins.values()]
        total_addresses = len(friend_coordinates)

        print("Calculating midpoint.")

        midpoint_lat = sum(lat for lat, lon in friend_coordinates) / total_addresses
        midpoint_lon = sum(lon for lat, lon in friend_coordinates) / total_addresses

        if total_addresses % 2 != 1:
            print("Odd number of coordinates.")

            farthest_coordinate = max(friend_coordinates, key=lambda coord: geodesic((midpoint_lat, midpoint_lon), coord).miles)

            dummy_latitude = 2 * midpoint_lat - farthest_coordinate[0]
            dummy_longitude = 2 * midpoint_lon - farthest_coordinate[1]

            latitude_b, longitude_b = dummy_latitude, dummy_longitude

            midpoint_lat = (latitude_a + latitude_b) / 2
            midpoint_lon = (longitude_a + longitude_b) / 2

        self.midpoint = (midpoint_lat, midpoint_lon)
        return self.midpoint

    
    def get_midpoint(self):
        if not self.friend_origins:
            return False

        latitude_a, longitude_a = self.get_coordinates(self.origin_a)

        friend_items = list(self.friend_origins.items())
        friend, address = friend_items[0]

        latitude_b, longitude_b = self.get_coordinates(address)

        midpoint_lat = (latitude_a + latitude_b) / 2
        midpoint_lon = (longitude_a + longitude_b) / 2

        self.midpoint = (midpoint_lat, midpoint_lon)
        return self.midpoint


    def find_midpoint_places(self):

        if self.midpoint == None:
            print("get_midpoint must be run first.")
            return False
        
        base_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        params = {
            "location": f"{self.midpoint[0]},{self.midpoint[1]}",
            "radius": self.radius,
            "keyword": self.search,
            "key": self.api_key,
        }

        response = requests.get(base_url, params=params)
        data = response.json()

        if data.get("results"):
            return data["results"]
        else:
            print("No places result data.")
            return None


    def get_directions_to_midpoint_places(self, many=False):

        suggested_places = []

        if not self.perform_search:
            return suggested_places

        places = self.find_midpoint_places() 

        if places:

            for idx, place in enumerate(places[:self.suggested_length]):

                distances = []
                durations = []

                place_coords = place['geometry']['location']['lat'], place['geometry']['location']['lng']

                distance_to_place_A = calculate_distance(self.get_coordinates(self.origin_a), place_coords)

                distances.append({"Me": distance_to_place_A})

                travel_time_A = calculate_travel_time(self.origin_a, place['vicinity'])

                durations.append({"Me": travel_time_A})

                if not many:

                    friend_items = list(self.friend_origins.items())
                    friend, address = friend_items[0]

                    distance_to_place = calculate_distance(self.get_coordinates(address), place_coords)
                    travel_time = calculate_travel_time(address, place['vicinity'])

                    distances.append({friend: distance_to_place})
                    durations.append({friend: travel_time})

                else:
                    for friend, address in self.friend_origins.items():
                        distance_to_place = calculate_distance(self.get_coordinates(address), place_coords)
                        travel_time = calculate_travel_time(address, place['vicinity'])

                        distances.append({friend: distance_to_place})
                        durations.append({friend: travel_time})

                suggested_places.append({
                    'name': place['name'],
                    'address': place['vicinity'],
                    'distances': distances,
                    'travel_times': durations,
                })

            return suggested_places
        else:
            return None


    def __str__(self):

        friends = ", ".join(friend for friend in self.friend_origins.keys())
        if len(self.friend_origins) > 1:
            friends = friends.rsplit(", ", 1)
            friends = " and ".join(friends)
        friends += "."
        print(friends)

        return f"Trip to {self.destination} with {friends}"