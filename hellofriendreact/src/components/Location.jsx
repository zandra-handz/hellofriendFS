// Location.js
import React, { useState } from 'react'; 
import CardExpandAndConfig from './DashboardStyling/CardExpandAndConfig';
import MessageSave from './DashboardStyling/MessageSave';
import MessageDelete from './DashboardStyling/MessageDelete';
import MessageError from './DashboardStyling/MessageError';


import { FaWrench } from 'react-icons/fa';
import FormLocation from './Forms/FormLocation';
import useAuthUser from '../hooks/UseAuthUser'; 
import api from '../api';
import '/src/styles/StylingDisplayEditableContent.css';


const Location = ({ location, friendList }) => {
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
    try {
      await api.delete(`/friends/location/${location.id}/`);
      setShowDeleteMessage(true);
      setTimeout(() => {
        setShowDeleteMessage(false);
      }, 3000);
      setIsCardVisible(false); // Hide the card after deletion
      console.log('Location deleted successfully.');
    } catch (error) {
      setShowErrorMessage(true);
      setTimeout(() => {
        setShowErrorMessage(false);
      }, 3000);
      console.error('Error deleting location:', error);
    }
  };

  const handleFriendSelect = (friendId) => {
    const updatedFriends = [...locationFriends];
    const friendIndex = updatedFriends.indexOf(friendId);
    if (friendIndex === -1) {
      updatedFriends.push(friendId);
    } else {
      updatedFriends.splice(friendIndex, 1);
    }
    setLocationFriends(updatedFriends);
  };

  const handleSubmit = async () => {
    try {
      await api.put(`/friends/location/${location.id}/`, {
        user: authUser.user.id,
        title: locationTitle,
        address: location.address,
        personal_experience_info: locationExperience,
        friends: locationFriends
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
                <p><strong>Friends:</strong> {locationFriends.map(friendId => friendList.find(friend => friend.id === friendId).name).join(', ')}</p>
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
