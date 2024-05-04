import React from 'react';
import '/src/styles/StylingFormsGeneral.css';

const FormFriendInfo = ({ friendData, handleInputChange, handleSubmit }) => {
  return (
    <div className="form-general-container">
      <label>
        Name:
        <input
          className="form-general-input"
          type="text"
          value={friendData.name}
          onChange={handleInputChange}
          name="name"
        />
      </label>
      <label>
        First Name:
        <input
          className="form-general-input"
          type="text"
          value={friendData.first_name}
          onChange={handleInputChange}
          name="first_name"
        />
      </label>
      <label>
        Last Name:
        <input
          className="form-general-input"
          type="text"
          value={friendData.last_name}
          onChange={handleInputChange}
          name="last_name"
        />
      </label>
      <div className="form-button-container">
        <button className="form-general-button" onClick={handleSubmit}>Save</button>
      </div>
    </div>
  );
};

export default FormFriendInfo;
