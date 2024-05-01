// LocationListProvider.jsx
import React, { createContext, useState, useEffect } from 'react';
import api from '../api';

const LocationListContext = createContext({});

export const LocationListProvider = ({ children }) => {
  const storedLocations = null; // Consider localStorage if needed
  const [locationList, setLocationList] = useState(storedLocations);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await api.get('/friends/locations/all/');
        const locationData = response.data;
        const extractedLocations = locationData.map(location => ({
          id: location.id,
          title: location.title,
          address: location.address,
          latitude: location.latitude,
          longitude: location.longitude,
          notes: location.personal_experience_info,
          friends: location.friends.map(friendId => ({ id: friendId })),
          validatedAddress: location.validated_address, // Include validated_address conditionally
        }));
        setLocationList(extractedLocations);
        console.log('Fetched Location Data:', extractedLocations);
      } catch (error) {
        console.error('Error fetching location list:', error);
      }
    };
  
    fetchData();
  }, []);
  

  return (
    <LocationListContext.Provider value={{ locationList, setLocationList }}>
      {children}
    </LocationListContext.Provider>
  );
};

export default LocationListContext;
