import React, { useEffect, useState } from 'react';
import api from '../api';
import EditCard from './DashboardStyling/EditCard';
import CardCreate from './DashboardStyling/CardCreate';
import useAuthUser from '../hooks/UseAuthUser'; 
import CreateLocation from './CreateLocation';
import useFriendList from '../hooks/UseFriendList'; // Import the useFriendList hook

const TabBarPageUserLocationsAll = () => {
    const [data, setData] = useState(null);
    const [editModes, setEditModes] = useState([]);
    const [locationTitles, setLocationTitles] = useState([]);
    const [locationExperiences, setLocationExperiences] = useState([]); // State to hold location experiences
    const [locationFriends, setLocationFriends] = useState([]); // State to hold location friends
    const [currentlyEditedIndex, setCurrentlyEditedIndex] = useState(null); // State to hold the index of the currently edited location
    const [showLocations, setShowLocations] = useState(false); // State to toggle visibility of locations
    const { authUser } = useAuthUser();
    const { friendList } = useFriendList(); // Fetch the list of friends
  
    useEffect(() => {
      if (showLocations) {
        const fetchData = async () => {
          try {
            const responseLocations = await api.get(`/friends/locations/all/`);
            setData(responseLocations.data);
            setEditModes(new Array(responseLocations.data.length).fill(false));
            setLocationTitles(responseLocations.data.map(location => location.title || ''));
            setLocationExperiences(responseLocations.data.map(location => location.personal_experience_info || '')); // Initialize location experiences state
            setLocationFriends(responseLocations.data.map(location => location.friends || [])); // Initialize location friends state
          } catch (error) {
            console.error('Error fetching data:', error);
          }
        };
        fetchData();
      }
    }, [showLocations]); // Fetch data only when showLocations state changes
  
    const toggleEditMode = (index) => {
      setEditModes(prevModes => {
        const updatedModes = [...prevModes];
        updatedModes[index] = !updatedModes[index];
        return updatedModes;
      });
      setCurrentlyEditedIndex(index); // Set the currently edited index when toggling edit mode
    };
  
    const handleInputChange = (e, index) => {
      const { name, value } = e.target;
      if (name === 'location-name') {
        setLocationTitles(prevTitles => {
          const updatedTitles = [...prevTitles];
          updatedTitles[index] = value;
          return updatedTitles;
        });
      } else if (name === 'location-experience') {
        setLocationExperiences(prevExperiences => {
          const updatedExperiences = [...prevExperiences];
          updatedExperiences[index] = value;
          return updatedExperiences;
        });
      }
    };

    const handleFriendSelect = (index, friendId) => {
      const updatedFriends = [...locationFriends[index]];
      const friendIndex = updatedFriends.indexOf(friendId);
      if (friendIndex === -1) {
        updatedFriends.push(friendId);
      } else {
        updatedFriends.splice(friendIndex, 1);
      }
      setLocationFriends(prevFriends => {
        const updatedLocations = [...prevFriends];
        updatedLocations[index] = updatedFriends;
        return updatedLocations;
      });
    };
  
    const handleSubmit = async (locationId, locationName, locationAddress, locationExperience, locationFriends) => {
      try {
        await api.put(`/friends/location/${locationId}/`, {
          user: authUser.user.id,
          title: locationName,
          address: locationAddress,
          personal_experience_info: locationExperience,
          friends: locationFriends // Include selected friends in the request body
        });
        const response = await api.get(`/friends/location/${locationId}/`);
        const updatedLocation = response.data;
        const updatedData = data.map(location => {
          if (location.id === updatedLocation.id) {
            return updatedLocation;
          }
          return location;
        });
        setData(updatedData);
        // Toggle edit mode back to view mode for the currently edited location
        setEditModes(prevModes => {
          const updatedModes = [...prevModes];
          updatedModes[currentlyEditedIndex] = false;
          return updatedModes;
        });
      } catch (error) {
        console.error('Error updating location:', error);
      }
    };
  
    return (
      <div>
        <CreateLocation />

        <button className="mass-function-button" onClick={() => setShowLocations(!showLocations)}>
          {showLocations ? 'Hide Locations' : 'Expand Saved Locations'}
        </button>

        {showLocations && (
          <>
            {data ? (
              data.map((location, index) => (
                <EditCard key={location.id} title={location.title || "Location"} onEditButtonClick={() => toggleEditMode(index)}>
                  {editModes[index] ? (
                    <div>
                      <div>
                        <h1>Location:</h1>
                        <input type="text" name="location-name" value={locationTitles[index]} onChange={(e) => handleInputChange(e, index)} />
                      </div>
                      <div>
                        <h1>Personal Experience:</h1>
                        <textarea name="location-experience" value={locationExperiences[index]} onChange={(e) => handleInputChange(e, index)} />
                      </div>
                      <div>
                        <h1>Friends:</h1>
                        {friendList.map(friend => (
                          <label key={friend.id}>
                            <input
                              type="checkbox"
                              checked={locationFriends[index].includes(friend.id)}
                              onChange={() => handleFriendSelect(index, friend.id)}
                            />
                            {friend.name}
                          </label>
                        ))}
                      </div>
                      <div>
                        <button onClick={() => handleSubmit(location.id, locationTitles[index], location.address, locationExperiences[index], locationFriends[index])}>Submit</button>
                      </div>
                    </div>
                  ) : (
                    <div>
                      <p><h1>Location:</h1>{location.title}</p>
                      <p><h1>Address:</h1>{location.address}</p>
                      <p><h1>Personal Experience Info:</h1>{location.personal_experience_info}</p>
                      <p><h1>Associated friends:</h1>{location.friends.map(friendId => friendList.find(friend => friend.id === friendId).name).join(', ')}</p>
                    </div>
                  )}
                </EditCard>
              ))
            ) : (
              <p>Loading...</p>
            )}
          </>
        )}
      </div>
    );
  };
  
  export default TabBarPageUserLocationsAll;
