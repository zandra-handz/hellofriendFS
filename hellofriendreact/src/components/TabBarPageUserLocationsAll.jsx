import React, { useEffect, useState } from 'react';
import api from '../api';
import useAuthUser from '../hooks/UseAuthUser'; 
import CreateLocation from './CreateLocation';
import useFriendList from '../hooks/UseFriendList'; // Import the useFriendList hook
import TabSpinner from './DashboardStyling/TabSpinner';
import { FaWrench } from 'react-icons/fa'; // Import the MessageSave component

import useLocationList from '../hooks/UseLocationList'; // Import the useLocationList hook


import Location from './Location';  
import MessageSave from './DashboardStyling/MessageSave'; 

const TabBarPageUserLocationsAll = () => {
  const [showLocations, setShowLocations] = useState(false);
  const [deletedMessage, setDeletedMessage] = useState(null);
  const [showSaveMessage, setShowSaveMessage] = useState(false);
  const { authUser } = useAuthUser();
  const { friendList } = useFriendList();
  const { locationList } = useLocationList();

  useEffect(() => {
    console.log('Location List:', locationList);
  }, [locationList]);

  const handleDelete = async (locationId) => {
    try {
      // Update the delete functionality if needed
      setDeletedMessage('Location deleted successfully.');
      setTimeout(() => {
        setDeletedMessage(null);
      }, 3000);
    } catch (error) {
      console.error('Error deleting location:', error);
    }
  };

  const handleAddLocation = (newLocation) => {
    // Update the add location functionality if needed
    setShowSaveMessage(true);
    setTimeout(() => {
      setShowSaveMessage(false);
    }, 3000);
  };

  return (
    <div>
      <CreateLocation onLocationCreate={handleAddLocation} />
      {showSaveMessage && <MessageSave sentenceObject={{ message: 'Location created successfully!' }} />}
      <button className="mass-function-button" onClick={() => setShowLocations(!showLocations)}>
        {showLocations ? 'Hide Locations' : 'Expand Saved Locations'}
      </button>
      {deletedMessage && <p>{deletedMessage}</p>}
      {showLocations && locationList ? (
        <>
          {locationList.length > 0 ? (
            Object.entries(locationList.reduce((acc, location) => {
              if (!acc[location.category]) {
                acc[location.category] = [];
              }
              acc[location.category].push(location);
              return acc;
            }, {})).map(([category, locations]) => (
              <div key={category}>
                <div>{category}</div>
                {locations.map(location => (
                  <div key={location.id}>
                    <Location
                      location={location}
                      friendList={friendList}
                      authUser={authUser}
                      onDelete={handleDelete}
                    />
                  </div>
                ))}
              </div>
            ))
          ) : (
            <TabSpinner />
          )}
        </>
      ) : null}
    </div>
  );
  
};

export default TabBarPageUserLocationsAll;
