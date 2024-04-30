import React from 'react';
import '/src/styles/StylingFormsGeneral.css';


const FormUserSettings = ({ receiveNotifications, languagePreference, largeText, highContrastMode, screenReader, handleInputChange, handleSubmit }) => {
  return (
    <div className="form-general-container">
      <label>
        Receive Notifications:
        <input
          type="checkbox"
          name="receiveNotifications"
          checked={receiveNotifications}
          onChange={handleInputChange}
        />
      </label>
      <label>
        Language Preference:
        <select
          name="languagePreference"
          value={languagePreference}
          onChange={handleInputChange}
          className="form-general-select"
        >
          <option value="en">English</option>
          <option value="es">Spanish</option>
        </select>
      </label>
      <label>
        Large Text:
        <input
          type="checkbox"
          name="largeText"
          checked={largeText}
          onChange={handleInputChange}
        />
      </label>
      <label>
        High Contrast Mode:
        <input
          type="checkbox"
          name="highContrastMode"
          checked={highContrastMode}
          onChange={handleInputChange}
        />
      </label>
      <label>
        Screen Reader:
        <input
          type="checkbox"
          name="screenReader"
          checked={screenReader}
          onChange={handleInputChange}
        />
      </label>
      <button className="form-general-button" onClick={handleSubmit}>Submit</button>
    </div>
  );
};

export default FormUserSettings;
