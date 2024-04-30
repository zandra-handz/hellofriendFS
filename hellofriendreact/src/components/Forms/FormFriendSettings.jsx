import React from 'react';
import '/src/styles/StylingFormsGeneral.css';

const FormFriendSettings = ({ effortRequired, priorityLevel, handleInputChange, handleSubmit }) => {
  return (
    <div className="form-general-container">
      <h6>Effort Required:</h6>
      <input
        className="form-general-input"
        type="range"
        min="1"
        max="5"
        value={effortRequired}
        onChange={handleInputChange}
        name="effort"
      />
      <h6>Priority Level:</h6>
      <input
        className="form-general-input"
        type="range"
        min="1"
        max="3"
        value={priorityLevel}
        onChange={handleInputChange}
        name="priority"
      />
      <button className="form-general-button" onClick={handleSubmit}>Submit</button>
    </div>
  );
};

export default FormFriendSettings;
