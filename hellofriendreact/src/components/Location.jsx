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

const Location = ({ location, friendList, locationList, setLocationList }) => {
  const [showForm, setShowForm] = useState(false);
  const [locationTitle, setLocationTitle] = useState(location.title || '');
  const [locationExperience, setLocationExperience] = useState(location.notes || '');
  const [locationFriends, setLocationFriends] = useState([]);
  const [expanded, setExpanded] = useState(false);
  const [showSaveMessage, setShowSaveMessage] = useState(false);
  const [showDeleteMessage, setShowDeleteMessage] = useState(false);
  const [showErrorMessage, setShowErrorMessage] = useState(false);
  const [isCardVisible, setIsCardVisible] = useState(true);
  const { authUser } = useAuthUser();

  useEffect(() => {
    console.log('Location friends:', location.friends);
    const updatedFriends = location.friends.map(friend => {
      const friendId = friend.id.id || friend.id; // Access the id property directly or from nested object
      const foundFriend = friendList.find(f => f.id === friendId);
      return foundFriend ? foundFriend : { id: friendId, name: 'Loading...' };
    });
    setLocationFriends(updatedFriends);
    console.log('Personal Experience Info:', location.notes);

    
  }, [location, friendList]);

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
        setIsCardVisible(false);
        
        const updatedLocationList = locationList.filter(loc => loc.id !== location.id);
        setLocationList(updatedLocationList);
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
      console.log('Updated friend list:', updatedFriends);
    }
  };
  
  const handleSubmit = async () => {
    try {
      // Extract friend IDs from locationFriends
      const friendIds = locationFriends.map(friend => friend.id);
  
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
      {isCardVisible && (
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
                  <div className="friends-container"> 
                    {locationFriends.map(friend => (
                      <span key={friend.id} className="friend-container">
                        {friend.name}
                      </span>
                    ))}
                  </div>
                </p> 
                {location.notes && (
                  <div>
                    <p><strong>Notes:</strong></p>
                    <p>{locationExperience}</p>
                  </div>
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
