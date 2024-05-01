import React, { useEffect, useState } from 'react';
import api from '../api';
import useAuthUser from '../hooks/UseAuthUser'; 
import CreateLocation from './CreateLocation';
import useFriendList from '../hooks/UseFriendList'; // Import the useFriendList hook
import TabSpinner from './DashboardStyling/TabSpinner';
import { FaWrench } from 'react-icons/fa';

import Location from './Location';  
import MessageSave from './DashboardStyling/MessageSave'; // Import the MessageSave component

const TabBarPageUserLocationsAll = () => {
  const [data, setData] = useState(null);
  const [showLocations, setShowLocations] = useState(false);
  const [deletedMessage, setDeletedMessage] = useState(null);
  const [showSaveMessage, setShowSaveMessage] = useState(false); // State to manage save message visibility
  const { authUser } = useAuthUser();
  const { friendList } = useFriendList();

  useEffect(() => {
    if (showLocations) {
      const fetchData = async () => {
        try {
          const responseLocations = await api.get(`/friends/locations/all/`);
          setData(responseLocations.data);
        } catch (error) {
          console.error('Error fetching data:', error);
        }
      };
      fetchData();
    }
  }, [showLocations]);

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

  const handleAddLocation = (newLocation) => {
    setData(prevData => [...prevData, newLocation]); // Add the new location to the list
    setShowSaveMessage(true); // Show the save message
    setTimeout(() => {
      setShowSaveMessage(false); // Hide the save message after 3 seconds
    }, 3000);
  };

  return (
    <div>
      <CreateLocation onLocationCreate={handleAddLocation} /> {/* Pass the callback function */}
      {showSaveMessage && <MessageSave sentenceObject={{ message: 'Location created successfully!' }} />} {/* Render the save message */}
      <button className="mass-function-button" onClick={() => setShowLocations(!showLocations)}>
        {showLocations ? 'Hide Locations' : 'Expand Saved Locations'}
      </button>
      {deletedMessage && <p>{deletedMessage}</p>}
      {showLocations && (
        <>
          {data ? (
            data.map((location, index) => (
              <div key={location.id}>
                <Location
                  location={location}
                  friendList={friendList}
                  authUser={authUser}
                  onDelete={handleDelete}
                />
                
              </div>
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