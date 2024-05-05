import React from 'react';
import '/src/styles/StylingFormsGeneral.css';


const FormLocation = ({ title, address, personalExperience, friends, friendList, handleInputChange, handleFriendSelect, handleSubmit }) => {
    return (
      <div className='form-general-container'> 
        <div>
          <h5>Edit name?</h5>
          <input
            className='form-general-input'  
            type="text"
            name="location-name"
            value={title}
            onChange={handleInputChange}
          />
        </div>
        <div>
          <h5>Edit notes?</h5>
          <textarea
            className='form-general-input'  
            name="location-experience"
            value={personalExperience}
            onChange={handleInputChange}
          />
        </div>
        <div className="friend-checkboxes-container"> 
          <h4>Edit friends?</h4>
          {friendList.map(friend => (
            <div className="checkbox-pair-container">
              <label key={friend.id}>
                <input
                  type="checkbox"
                  checked={friends.includes(friend)}
                  onChange={() => handleFriendSelect(friend.id)}
                />
                {friend.name}
              </label>
            </div>
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