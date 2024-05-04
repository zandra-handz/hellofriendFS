import React, { useState, useEffect } from 'react'; 
import CardExpandAndConfig from './DashboardStyling/CardExpandAndConfig';
import MessageSave from './DashboardStyling/MessageSave';
import MessageDelete from './DashboardStyling/MessageDelete';
import MessageError from './DashboardStyling/MessageError';
import { FaWrench } from 'react-icons/fa';
import FormLocation from './Forms/FormLocation';
import useAuthUser from '../hooks/UseAuthUser'; 
import api from '../api';
import '/src/styles/StylingDisplayEditableContent.css';

const Location = ({ location, friendList, locationList, setLocationList }) => { // Update the props
  const [showForm, setShowForm] = useState(false);
  const [locationTitle, setLocationTitle] = useState(location.title || '');
  const [locationExperience, setLocationExperience] = useState(location.personal_experience_info || '');
  const [locationFriends, setLocationFriends] = useState(location.friends || []);
  const [expanded, setExpanded] = useState(false);
  const [showSaveMessage, setShowSaveMessage] = useState(false);
  const [showDeleteMessage, setShowDeleteMessage] = useState(false);
  const [showErrorMessage, setShowErrorMessage] = useState(false);
  const [isCardVisible, setIsCardVisible] = useState(true); // State to manage card visibility
  const { authUser } = useAuthUser();

  useEffect(() => {
    console.log('Location prop:', location);
  }, [location]);

  const toggleForm = () => {
    setShowForm(prevState => !prevState);
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    if (name === 'location-name') {
      setLocationTitle(value);
    } else if (name === 'location-experience') {
      setLocationExperience(value);
    }
  };

  const handleDelete = async () => {
    const confirmed = window.confirm('Are you sure you want to delete this location?');
    if (confirmed) {
      try {
        await api.delete(`/friends/location/${location.id}/`);
        setShowDeleteMessage(true);
        setTimeout(() => {
          setShowDeleteMessage(false);
        }, 3000);
        setIsCardVisible(false); // Hide the card after deletion
        
        // Remove the deleted location from the locationList
        const updatedLocationList = locationList.filter(loc => loc.id !== location.id);
        setLocationList(updatedLocationList); // Update the location list
        console.log('Location deleted successfully.');
      } catch (error) {
        setShowErrorMessage(true);
        setTimeout(() => {
          setShowErrorMessage(false);
        }, 3000);
        console.error('Error deleting location:', error);
      }
    }
  };

  const handleFriendSelect = (friendId) => {
    console.log('Selected friend ID:', friendId); // Log the selected friend ID
    const friend = friendList.find(friend => friend.id === friendId);
    if (friend) {
      const updatedFriends = [...locationFriends];
      const friendIndex = updatedFriends.findIndex(f => f.id === friendId);
      if (friendIndex === -1) {
        updatedFriends.push(friend);
      } else {
        updatedFriends.splice(friendIndex, 1);
      }
      setLocationFriends(updatedFriends);
      console.log('Updated friend list:', updatedFriends); // Log the updated friend list
    }
  };
  
  

const handleSubmit = async () => {
  try {
    // Extract friend IDs from locationFriends
    const friendIds = locationFriends.map(friend => friend.id);
    console.log("friendIds in submit: ", friendIds)

    // Make the PUT request with the friendIds array
    await api.put(`/friends/location/${location.id}/`, {
      user: authUser.user.id,
      title: locationTitle,
      address: location.address,
      personal_experience_info: locationExperience,
      friends: friendIds // Use friendIds array instead of locationFriends
    });

    

    setShowSaveMessage(true);
    setTimeout(() => {
      setShowSaveMessage(false);
    }, 3000);
    setShowForm(false);
    console.log('Location updated successfully.');
  } catch (error) {
    setShowErrorMessage(true);
    setTimeout(() => {
      setShowErrorMessage(false);
    }, 3000);
    console.error('Error updating location:', error);
  }
};


  const toggleExpand = () => {
    setExpanded(prevExpanded => !prevExpanded);
  };

  return (
    <>
      {isCardVisible && ( // Render the card only if it's visible
        <CardExpandAndConfig
          title={location.title || "Location"}
          expanded={expanded}
          onCardExpandClick={toggleExpand}
        >
          <div className="display-editable-content">
            <div className="display-editable-content-header">
              <h4>{location.address !== location.title ? location.address : "No address"}</h4>
              <div>
                <button className="edit-button" onClick={toggleForm}>
                  <FaWrench />
                </button>
              </div>
            </div>
            {showForm ? (
              <FormLocation
                title={locationTitle}
                personalExperience={locationExperience}
                friends={locationFriends}
                friendList={friendList}
                handleInputChange={handleInputChange}
                handleFriendSelect={handleFriendSelect}
                handleSubmit={handleSubmit}
              />
            ) : ( 

              <div>
                <p><strong>Friends:</strong> 
                  {locationFriends.map(friend => (
                    <span key={friend.id} className="friend-container">
                      {friend.name}
                    </span>
                  ))}
                </p> 

                
                {location.personal_experience_info && (
                <p><strong>Notes about this location:</strong> {location.personal_experience_info}</p>
                )}
              </div>
            )}
            <button className="mass-function-button" onClick={handleDelete}>
              Delete
            </button>
            {showSaveMessage && <MessageSave sentenceObject={{ message: 'Location saved successfully!' }} />}
            {showDeleteMessage && <MessageDelete sentenceObject={{ message: 'Location deleted successfully!' }} />}
            {showErrorMessage && <MessageError sentenceObject={{ message: 'Error occurred!' }} />}
          </div>
        </CardExpandAndConfig>
      )}
    </>
  );
};

export default Location;
