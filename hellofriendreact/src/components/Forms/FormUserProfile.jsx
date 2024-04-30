import React from 'react';
import '/src/styles/StylingFormsGeneral.css';


const FormUserProfile = ({ firstName = '', lastName = '', dateOfBirth = '', gender = '', handleInputChange, handleSubmit }) => {
    return (
      <div className="form-general-container">
        <label>
          First Name:
          <input
            type="text"
            name="firstName"
            value={firstName}
            onChange={handleInputChange}
            className="form-general-input"
          />
        </label>
        <label>
          Last Name:
          <input
            type="text"
            name="lastName"
            value={lastName}
            onChange={handleInputChange}
            className="form-general-input"
          />
        </label>
        <label>
          Date of Birth:
          <input
            type="date"
            name="dateOfBirth"
            value={dateOfBirth}
            onChange={handleInputChange}
            className="form-general-input"
          />
        </label>
        <label>
          Gender:
          <select
            name="gender"
            value={gender}
            onChange={handleInputChange}
            className="form-general-select"
          >
            <option value="NB">Non-Binary</option>
            <option value="M">Male</option>
            <option value="F">Female</option>
            <option value="O">Other</option>
            <option value="No answer">Uninterested in answering this</option>
          </select>
        </label>
        <button className="form-general-button" onClick={handleSubmit}>Submit</button>
      </div>
    );
  };
  
  export default FormUserProfile;