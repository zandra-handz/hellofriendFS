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
import re


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


class PlaceDetailsFetcher:
    def __init__(self, place_id):
        self.place_id = place_id
        self.api_key = api_key

    def get_place_details(self):
        url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={self.place_id}&fields=name,formatted_address,formatted_phone_number,rating,photos,reviews,opening_hours,geometry&key={self.api_key}"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()

    def extract_place_details(self, data):
        result = data.get('result', {})
        photos = result.get('photos', [])
        photo_references = [photo.get('photo_reference') for photo in photos]
        photo_urls = [f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={ref}&key={self.api_key}" for ref in photo_references]

        reviews = result.get('reviews', [])
        review_details = [
            {
                'author_name': review.get('author_name'),
                'rating': review.get('rating'),
                'text': review.get('text'),
                'time': review.get('time')
            }
            for review in reviews
        ]

        hours = result.get('opening_hours', {}).get('weekday_text', [])

        return {
            'name': result.get('name'),
            'address': result.get('formatted_address'),
            'phone': result.get('formatted_phone_number'),
            'rating': result.get('rating'),
            'photos': photo_urls,
            'reviews': review_details,
            'hours': result.get('opening_hours'),
        }



class GeocodingFetcher:
    def __init__(self, address=None, lat=None, lon=None):
        self.address = address
        self.lat = lat
        self.lon = lon
        self.api_key = api_key

    def get_place_id(self):
        if self.address:
            url = f"https://maps.googleapis.com/maps/api/geocode/json?address={self.address}&key={self.api_key}"
        else:
            url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={self.lat},{self.lon}&key={self.api_key}"

        response = requests.get(url)
        response.raise_for_status()
        results = response.json().get('results', [])

        if results:
            return results[0].get('place_id')
        else:
            raise ValueError("No place ID found for the given address or coordinates.")

class PlaceDetailsFetcherOld:
    def __init__(self, origin_address=None, origin_lat=None, origin_lon=None, get_coords_from_google=True):
        self.api_key = api_key
        self.origin_address = origin_address
        self.origin_lat = origin_lat
        self.origin_lon = origin_lon
        self.get_coords_from_google = get_coords_from_google

        if self.get_coords_from_google:
            if self.origin_address:
                if not self.validate_address(origin_address):
                    raise ValueError(f"Invalid address: {origin_address}")
                else:
                    try:
                        descriptive_data = self.get_coordinates_and_formatted_address(self.origin_address)
                        self.assign_origin_coords(descriptive_data[0], descriptive_data[1])
                        self.assign_address(descriptive_data[2])
                    except Exception as e:
                        print(f"An error occurred: {e}")
        else:
            if not self.origin_lat or not self.origin_lon:
                raise ValueError("Coordinates not provided")

    def validate_address(self, address):
        return validate_address(address)

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
            raise ValueError(f"Unable to retrieve coordinates for {address}")


    def assign_origin_coords(self, latitude, longitude):
        self.origin_lat = latitude
        self.origin_lon = longitude
        return self.origin_lat, self.origin_lon

    def assign_address(self, formatted_address):
        self.origin_address = formatted_address
        return self.origin_address
    
    def get_nearest_place_id(self):
        if not self.origin_lat or not self.origin_lon:
            raise ValueError("Coordinates are required.")
        
        base_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        params = {
            "location": f"{self.origin_lat},{self.origin_lon}",
            "radius": 3,  # Small radius to get the closest place
            "key": self.api_key,
        }

        response = requests.get(base_url, params=params)
        data = response.json()

        if data.get("results"):
            nearest_place = data["results"][0]  # Get the first result
            return nearest_place.get("place_id")  # Ensure place_id is correctly returned
        else:
            raise ValueError("No nearby place found.")

    def get_place_details(self, place_id):
        details_url = "https://maps.googleapis.com/maps/api/place/details/json"
        params = {
            "place_id": place_id,
            "key": self.api_key,
        }

        response = requests.get(details_url, params=params)
        details_data = response.json()

        if details_data.get("result"):
            return details_data["result"]
        else:
            print(f"No details found for place_id: {place_id}")
            return None

    def extract_place_details(self, place_details):
        return {
            "name": place_details.get("name"),
            "formatted_address": place_details.get("formatted_address"),
            "opening_hours": place_details.get("opening_hours"),
            "business_status": place_details.get("business_status"),
            "photos": [photo.get("photo_reference") for photo in place_details.get("photos", [])],
            "reviews": place_details.get("reviews", []),
            "formatted_phone_number": place_details.get("formatted_phone_number"),
            "rating": place_details.get("rating"),
        }





class NearbyDetails:
    def __init__(self, origin_address, origin_lat=None, origin_lon=None, radius=5000, search="", use_search=False, get_coords_from_google=True, return_items=3):
        self.api_key = api_key
        self.origin_address = origin_address
        self.origin_lat = origin_lat
        self.origin_lon = origin_lon
        self.radius = radius
        self.search = search
        self.use_search = use_search
        self.return_items = return_items
        self.get_coords_from_google = get_coords_from_google

        if self.get_coords_from_google:
            if self.origin_address:
                if not self.validate_address(origin_address):
                    raise ValueError(f"Invalid address: {origin_address}")
        else:
            if not self.origin_lat or not self.origin_lon:
                raise ValueError(f"Coordinates not communicated to backend")

    def validate_address(self, address):
        # Implement address validation if needed
        return True

    def assign_origin_coords(self, latitude, longitude):
        self.origin_lat = latitude
        self.origin_lon = longitude
        return self.origin_lat, self.origin_lon

    def assign_address(self, formatted_address):
        self.origin_address = formatted_address
        return self.origin_address

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

    def find_places(self):
        if self.get_coords_from_google:
            try:
                descriptive_data = self.get_coordinates_and_formatted_address(self.origin_address)
                self.assign_origin_coords(descriptive_data[0], descriptive_data[1])
                self.assign_address(descriptive_data[2])
            except Exception as e:
                print(f"An error occurred: {e}")

        if not self.origin_lat or not self.origin_lon:
            raise ValueError("Coordinates are required.")

        nearest_place_id = self.get_nearest_place_id(self.origin_lat, self.origin_lon)
        nearest_place_details = self.get_place_details(nearest_place_id) if nearest_place_id else None

        base_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        params = {
            "location": f"{self.origin_lat},{self.origin_lon}",
            "radius": self.radius,
            "keyword": self.search,
            "key": self.api_key,
        }

        response = requests.get(base_url, params=params)
        data = response.json()

        detailed_places = []

        if data.get("results"):
            places = data["results"]

            # Include nearest place details at the top of the list if available
            if nearest_place_details:
                detailed_places.append(self.extract_place_details(nearest_place_details))

            for place in places:
                place_id = place["place_id"]
                if place_id != nearest_place_id:  # Skip the nearest place already added
                    details = self.get_place_details(place_id)
                    if details:
                        detailed_places.append(self.extract_place_details(details))

                if len(detailed_places) >= self.return_items:
                    break

            return detailed_places
        else:
            print("No places result data.")
            return None

    def extract_place_details(self, place_details):
        return {
            "name": place_details.get("name"),
            "formatted_address": place_details.get("formatted_address"),
            "opening_hours": place_details.get("opening_hours"),
            "business_status": place_details.get("business_status"),
            "photos": [photo.get("photo_reference") for photo in place_details.get("photos", [])],
            "reviews": place_details.get("reviews", []),
            "formatted_phone_number": place_details.get("formatted_phone_number"),
            "rating": place_details.get("rating"),
        }



    def get_nearest_place_id(self, lat, lon):
        base_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        params = {
            "location": f"{lat},{lon}",
            "radius": 50,  # Small radius to get the closest place
            "key": self.api_key,
        }

        response = requests.get(base_url, params=params)
        data = response.json()

        if data.get("results"):
            nearest_place = data["results"][0]  # Get the first result
            return nearest_place["place_id"]
        else:
            print("No nearby place found.")
            return None

    def get_place_details(self, place_id):
        details_url = "https://maps.googleapis.com/maps/api/place/details/json"
        params = {
            "place_id": place_id,
            "key": self.api_key,
        }

        response = requests.get(details_url, params=params)
        details_data = response.json()

        if details_data.get("result"):
            return details_data["result"]
        else:
            print(f"No details found for place_id: {place_id}")
            return None



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




    def parse_travel_time(self, travel_time_str):
        """
        Parse the travel time string to extract the numeric value in minutes.
        Assumes the format can be like "5 mins", "16 mins", "2 hours 56 mins", etc.
        """
        try:
            # Initialize minutes and hours
            minutes = 0
            hours = 0
            
            # Regex patterns to match hours and minutes
            hours_match = re.search(r'(\d+)\s*hours?', travel_time_str, re.IGNORECASE)
            minutes_match = re.search(r'(\d+)\s*mins?', travel_time_str, re.IGNORECASE)
            
            # Extract hours and minutes if present
            if hours_match:
                hours = int(hours_match.group(1))
            if minutes_match:
                minutes = int(minutes_match.group(1))
            
            # Convert hours to minutes and add to minutes
            total_minutes = hours * 60 + minutes
            return total_minutes

        except ValueError:
            print(f"Error parsing travel time: {travel_time_str}")
            return 0

    def get_directions_to_midpoint_places(self, many=False):
        suggested_places = []

        if not self.perform_search:
            return suggested_places

        places = self.find_midpoint_places() 

        if places:
            for idx, place in enumerate(places[:self.suggested_length]):

                distances = []
                durations = []
                distance_difference = 0
                time_difference = 0

                try:
                    # Extract latitude and longitude
                    place_coords = (place['geometry']['location']['lat'], place['geometry']['location']['lng'])
                    lat, lon = place_coords

                    # Calculate distance from origin_a to place
                    distance_to_place_A = calculate_distance(self.get_coordinates(self.origin_a), place_coords)
                    distances.append({"Me": distance_to_place_A})

                    # Calculate travel time from origin_a to place
                    travel_time_A = calculate_travel_time(self.origin_a, place['vicinity'])
                    # Debug: Print raw travel time
                    print(f"Raw travel_time_A: {travel_time_A}")

                    # Parse and convert to float
                    travel_time_A = self.parse_travel_time(travel_time_A)
                    if travel_time_A is not None:  # Ensure travel time is valid
                        durations.append({"Me": travel_time_A})
                    else:
                        durations.append({"Me": 0})  # Default to 0 if parsing fails

                    if not many:
                        friend_items = list(self.friend_origins.items())
                        if friend_items:
                            friend, address = friend_items[0]

                            # Calculate distance from friend origin to place
                            distance_to_place = calculate_distance(self.get_coordinates(address), place_coords)
                            distances.append({friend: distance_to_place})

                            # Calculate travel time from friend origin to place
                            travel_time = calculate_travel_time(address, place['vicinity'])
                            # Debug: Print raw travel time for friend
                            print(f"Raw travel_time for {friend}: {travel_time}")

                            # Parse and convert to float
                            travel_time = self.parse_travel_time(travel_time)
                            if travel_time is not None:  # Ensure travel time is valid
                                durations.append({friend: travel_time})
                            else:
                                durations.append({friend: 0})  # Default to 0 if parsing fails

                            # Compute differences
                            distance_difference = abs(distance_to_place_A - distance_to_place)
                            time_difference = abs(travel_time_A - travel_time)
                    else:
                        for friend, address in self.friend_origins.items():
                            # Calculate distance from friend origin to place
                            distance_to_place = calculate_distance(self.get_coordinates(address), place_coords)
                            distances.append({friend: distance_to_place})

                            # Calculate travel time from friend origin to place
                            travel_time = calculate_travel_time(address, place['vicinity'])
                            # Debug: Print raw travel time for friend
                            print(f"Raw travel_time for {friend}: {travel_time}")

                            # Parse and convert to float
                            travel_time = self.parse_travel_time(travel_time)
                            if travel_time is not None:  # Ensure travel time is valid
                                durations.append({friend: travel_time})
                            else:
                                durations.append({friend: 0})  # Default to 0 if parsing fails

                            # Compute differences
                            if distances:
                                last_distance = next(iter(distances[-1].values()))  # Get the last distance value
                                last_time = next(iter(durations[-1].values()))  # Get the last time value

                                try:
                                    last_time = float(last_time)  # Ensure last_time is a number
                                except ValueError:
                                    print(f"Conversion error for last_time: {last_time}")
                                    last_time = 0

                                distance_difference = abs(distance_to_place_A - last_distance)
                                time_difference = abs(travel_time_A - last_time)

                    suggested_places.append({
                        'name': place['name'],
                        'address': place['vicinity'],
                        'latitude': lat,  # Add latitude
                        'longitude': lon,  # Add longitude
                        'distances': distances,
                        'travel_times': durations,
                        'distance_difference': distance_difference,
                        'time_difference': time_difference,
                    })

                except KeyError as e:
                    print(f"KeyError: {e} - Check if the place data structure is correct.")
                    continue
                except Exception as e:
                    print(f"Error: {e} - Unexpected error.")
                    continue

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