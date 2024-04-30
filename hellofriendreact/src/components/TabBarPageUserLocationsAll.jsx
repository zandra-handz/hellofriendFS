import React, { useEffect, useState } from 'react';
import api from '../api';
import useAuthUser from '../hooks/UseAuthUser'; 
import CreateLocation from './CreateLocation';
import useFriendList from '../hooks/UseFriendList'; // Import the useFriendList hook
import TabSpinner from './DashboardStyling/TabSpinner';
import { FaWrench } from 'react-icons/fa';

import Location from './Location'; 

const TabBarPageUserLocationsAll = () => {
  const [data, setData] = useState(null);
  const [editModes, setEditModes] = useState([]);
  const [locationTitles, setLocationTitles] = useState([]);
  const [locationExperiences, setLocationExperiences] = useState([]);
  const [locationFriends, setLocationFriends] = useState([]);
  const [currentlyEditedIndex, setCurrentlyEditedIndex] = useState(null);
  const [showLocations, setShowLocations] = useState(false);
  const [deletedMessage, setDeletedMessage] = useState(null); // New state for deleted message
  const { authUser } = useAuthUser();
  const { friendList } = useFriendList();

  useEffect(() => {
    if (showLocations) {
      const fetchData = async () => {
        try {
          const responseLocations = await api.get(`/friends/locations/all/`);
          setData(responseLocations.data);
          setEditModes(new Array(responseLocations.data.length).fill(false));
          setLocationTitles(responseLocations.data.map(location => location.title || ''));
          setLocationExperiences(responseLocations.data.map(location => location.personal_experience_info || ''));
          setLocationFriends(responseLocations.data.map(location => location.friends || []));
        } catch (error) {
          console.error('Error fetching data:', error);
        }
      };
      fetchData();
    }
  }, [showLocations]);

  const toggleEditMode = (index) => {
    setEditModes(prevModes => {
      const updatedModes = [...prevModes];
      updatedModes[index] = !updatedModes[index];
      return updatedModes;
    });
    setCurrentlyEditedIndex(index);
  };

  const handleDelete = async (locationId) => {
    try {
      await api.delete(`/friends/location/${locationId}/`);
      setData(prevData => prevData.filter(location => location.id !== locationId));
      setDeletedMessage('Location deleted successfully.'); 
       
      setTimeout(() => {
        setDeletedMessage(null);
      }, 3000);
    } catch (error) {
      console.error('Error deleting location:', error);
    }
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
          friends: locationFriends
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
        {deletedMessage && <p>{deletedMessage}</p>} {/* Render deleted message */}
        {showLocations && (
          <>
            {data ? (
              data.map((location, index) => (
                <Location
                  key={location.id}
                  location={location}
                  index={index}
                  editMode={editModes[index]}
                  handleToggleEditMode={toggleEditMode}
                  handleInputChange={handleInputChange}
                  handleSubmit={handleSubmit}
                  handleDelete={handleDelete}
                  friendList={friendList}
                />
              ))
            ) : (
              <TabSpinner />
            )}
          </>
        )}
      </div>
    );
  };
  
  export default TabBarPageUserLocationsAll;
