import React from 'react';
import '/src/styles/StylingFormsGeneral.css';


const FormLocation = ({ title, address, personalExperience, friends, friendList, handleInputChange, handleFriendSelect, handleSubmit }) => {
    return (
      <div className='form-general-container'> 
        <div>
          <h1>Location:</h1>
          <input
            className='form-general-input'  
            type="text"
            name="location-name"
            value={title}
            onChange={handleInputChange}
          />
        </div>
        <div>
          <h1>Personal Experience:</h1>
          <textarea
            className='form-general-input'  
            name="location-experience"
            value={personalExperience}
            onChange={handleInputChange}
          />
        </div>
        <div className="friend-checkboxes-container"> 
          <h1>Friends:</h1>
          {friendList.map(friend => (
            <label key={friend.id}>
              <input
                type="checkbox"
                checked={friends.includes(friend)}
                onChange={() => handleFriendSelect(friend.id)}
              />
              {friend.name}
            </label>
          ))}
        </div>
        <div>
          <button className='form-general-button' onClick={handleSubmit}> {/* Added className */}
            Submit
          </button>
        </div>
      </div>
    );
  };
  
  export default FormLocation;