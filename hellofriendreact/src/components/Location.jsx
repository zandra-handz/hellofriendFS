// Location.js
import React, { useState } from 'react'; 
import CardExpandAndConfig from './DashboardStyling/CardExpandAndConfig';
import { FaWrench } from 'react-icons/fa';
import FormLocation from './Forms/FormLocation';

const Location = ({ location, index, editMode, handleToggleEditMode, handleInputChange, handleSubmit, handleDelete, friendList }) => {
  const [showForm, setShowForm] = useState(false);

  const toggleForm = () => {
    setShowForm(prevState => !prevState);
  };

  return (
    <CardExpandAndConfig
      title={location.title || "Location"}
      expanded={editMode}
      onEditButtonClick={() => handleToggleEditMode(index)}
    >
      <>
        <div className="edit-card-header">
          <h5>Location</h5>
          <button className="edit-button" onClick={() => toggleForm()}>
            <FaWrench />
          </button>
        </div>
        {showForm ? (
          <FormLocation
            title={location.title}
            personalExperience={location.personal_experience_info}
            friends={location.friends}
            friendList={friendList}
            handleInputChange={(e) => handleInputChange(e, index)}
            handleFriendSelect={(friendId) => handleFriendSelect(index, friendId)}
            handleSubmit={() => handleSubmit(location.id)}
          />
        ) : (
          <div>
            <p><h1>Location:</h1>{location.title}</p>
            <p><h1>Address:</h1>{location.address}</p>
            <p><h1>Personal Experience Info:</h1>{location.personal_experience_info}</p>
            <p><h1>Associated friends:</h1>{location.friends.map(friendId => friendList.find(friend => friend.id === friendId).name).join(', ')}</p>
          </div>
        )}
        <button onClick={() => handleDelete(location.id)}>Delete</button>
      </>
    </CardExpandAndConfig>
  );
};

export default Location;
