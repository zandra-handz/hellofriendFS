import React, { useEffect, useState } from 'react';
import api from '../api';
import CardConfig from './DashboardStyling/CardConfig';
import Spinner from './DashboardStyling/Spinner';
import useAuthUser from '../hooks/UseAuthUser';

const UserSettings = () => {
  const [data, setData] = useState(null);
  const [isEditMode, setIsEditMode] = useState(false);
  const [receiveNotifications, setReceiveNotifications] = useState(false);
  const [languagePreference, setLanguagePreference] = useState('');
  const [largeText, setLargeText] = useState(false);
  const [highContrastMode, setHighContrastMode] = useState(false);
  const [screenReader, setScreenReader] = useState(false);
  const { authUser } = useAuthUser();

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await api.get(`/users/${authUser.user.id}/settings/`);
        setData(response.data);
        setReceiveNotifications(response.data.receive_notifications);
        setLanguagePreference(response.data.language_preference);
        setLargeText(response.data.large_text);
        setHighContrastMode(response.data.high_contrast_mode);
        setScreenReader(response.data.screen_reader);
      } catch (error) {
        console.error('Error fetching user settings:', error);
      }
    };
    fetchData();
  }, []);

  const toggleEditMode = () => {
    setIsEditMode(prevMode => !prevMode);
  };

  const handleInputChange = (e) => {
    const { name, checked, value } = e.target;
    // Update corresponding state based on input field name
    switch (name) {
      case 'receiveNotifications':
        setReceiveNotifications(checked);
        break;
      case 'languagePreference':
        setLanguagePreference(value);
        break;
      case 'largeText':
        setLargeText(checked);
        break;
      case 'highContrastMode':
        setHighContrastMode(checked);
        break;
      case 'screenReader':
        setScreenReader(checked);
        break;
      default:
        break;
    }
  };

  const handleSubmit = async () => {
    try {
      await api.put(`/users/${authUser.user.id}/settings/update/`, {
        user: authUser.user.id,
        receive_notifications: receiveNotifications,
        language_preference: languagePreference,
        large_text: largeText,
        high_contrast_mode: highContrastMode,
        screen_reader: screenReader
      });
      // Assuming the update is successful, we can set edit mode to false to switch back to view mode
      setIsEditMode(false);
      fetchData();
    } catch (error) {
      console.error('Error updating user settings:', error);
    }
  };

  return (
    <CardConfig title="User Settings" onEditButtonClick={toggleEditMode}>
      {isEditMode ? (
        <div>
          <div>
            <label>
              Receive Notifications:
              <input type="checkbox" name="receiveNotifications" checked={receiveNotifications} onChange={handleInputChange} />
            </label>
          </div>
          <div>
            <label>
              Language Preference:
              <select name="languagePreference" value={languagePreference} onChange={handleInputChange}>
                <option value="en">English</option>
                <option value="es">Spanish</option>
              </select>
            </label>
          </div>
          <div>
            <label>
              Large Text:
              <input type="checkbox" name="largeText" checked={largeText} onChange={handleInputChange} />
            </label>
          </div>
          <div>
            <label>
              High Contrast Mode:
              <input type="checkbox" name="highContrastMode" checked={highContrastMode} onChange={handleInputChange} />
            </label>
          </div>
          <div>
            <label>
              Screen Reader:
              <input type="checkbox" name="screenReader" checked={screenReader} onChange={handleInputChange} />
            </label>
          </div>
          <div>
            <button onClick={handleSubmit}>Submit</button>
          </div>
        </div>
      ) : (
        <div>
          {data ? (
            <div>
              <p>Receive Notifications: {receiveNotifications ? 'Enabled' : 'Disabled'}</p>
              <p>Language Preference: {languagePreference}</p>
              <p>Large Text: {largeText ? 'Enabled' : 'Disabled'}</p>
              <p>High Contrast Mode: {highContrastMode ? 'Enabled' : 'Disabled'}</p>
              <p>Screen Reader: {screenReader ? 'Enabled' : 'Disabled'}</p>
            </div>
          ) : (
            <Spinner />
          )}
        </div>
      )}
    </CardConfig>
  );
};

export default UserSettings;
