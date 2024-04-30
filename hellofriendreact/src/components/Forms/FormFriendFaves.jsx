import React from 'react';
import '/src/styles/StylingFormsGeneral.css';


const FormFriendFaves = ({ locations }) => {
  return (
    <div className="form-general-container">
      <h6>Locations:</h6>
      <select className="form-general-input">
        {locations.map(location => (
          <option key={location.id} value={location.id}>{location.name}</option>
        ))}
      </select>
    </div>
  );
};

export default FormFriendFaves;