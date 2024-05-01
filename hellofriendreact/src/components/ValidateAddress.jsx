import React, { useState, useEffect } from 'react';
import api from '../api';
import { FaCheck, FaUndo, FaArrowCircleUp } from 'react-icons/fa';
import useAuthUser from '/src/hooks/UseAuthUser';
import useSelectedFriend from '/src/hooks/UseSelectedFriend';
import useThemeMode from '../hooks/UseThemeMode';
import '/src/styles/OldStyles.css';
import useLocationList from '../hooks/UseLocationList'; // Import the useLocationList hook

const ValidateAddress = ({ headerText, onValidationChange }) => {
  const { themeMode } = useThemeMode();
  const [selectedAddress, setSelectedAddress] = useState('');
  const [inputAddress, setInputAddress] = useState('');
  const [validatedText, setValidatedText] = useState('');
  const { selectedFriend } = useSelectedFriend();
  const { authUser } = useAuthUser();
  const { locationList } = useLocationList(); // Get locationList from context

  useEffect(() => {
    console.log('Location List in ValidateAddress:', locationList);
    // Fetch saved addresses when the component mounts
    setInputAddress('');
    setSelectedAddress('');
    setValidatedText('');
  }, [locationList]); // Reload data when locationList changes

  const handleValidation = async () => {
    try {
      const response = await api.post(`/friends/location/validate-only/`, {
        user: authUser.user.id,
        address: inputAddress,
      });

      console.log('Validation Response:', response.data);

      if (response.data.address && response.data.latitude && response.data.longitude) {
        // Notify parent component of validation changes
        onValidationChange(true, response.data.address, response.data.latitude, response.data.longitude);
        // Set the validated text
        setValidatedText(response.data.address);
      }
    } catch (error) {
      console.error('Error validating address:', error);
    }
  };

  const handleSelectChange = (e) => {
    const value = e.target.value;
    setSelectedAddress(value);
    setInputAddress('');
    if (value) {
      // Only call onValidationChange if a saved address is selected
      const selectedOption = locationList.find(location => location.address === value);
      if (selectedOption) {
        const { address, latitude, longitude } = selectedOption;
        onValidationChange(true, address, latitude, longitude);
        setValidatedText(address);
      }
    }
  };

  const handleInputChange = (e) => {
    const value = e.target.value;
    setInputAddress(value);
    // Clear selected address when input changes
    setSelectedAddress('');
    // Clear the validated text
    setValidatedText('');
  };
  
    
  return (
    <div style={{ position: 'relative' }}>
      <div style={{ position: 'relative', zIndex: 0 }}>
        <div style={{ padding: '0px' }}>
          <h2>{headerText}</h2>
        </div>
        <div style={{ position: 'relative' }}>
          <input
            type="text"
            placeholder=""
            value={inputAddress}
            onChange={handleInputChange}
            style={{ position: 'absolute', borderRadius: '20px',  left: '6px', top: '3px', zIndex: 1, width: '80%', paddingRight: '0' }}
          />
          <button
            onClick={handleValidation}
            style={{ position: 'absolute', right: 0, zIndex: 0, width: '40px'}}
            className="places-card-validate-button"  
          >
            <FaArrowCircleUp />
          </button>
          <div className="custom-dropdown">
            <select
              id="addressSelect"
              value={selectedAddress}
              onChange={handleSelectChange}
            >
              <option value="">Select saved address</option>
              {locationList && locationList.map(location => (
                <option key={location.id} value={location.address}>
                  {location.title} - {location.address}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>
      {validatedText && (
        <div style={{ position: 'absolute', right: 0, left: -2, top: 28, color: 'black', display: 'flex', fontSize: '21px', zIndex: 0 }}>
          <label>{validatedText}  <FaCheck style={{ color: 'transparent' }} /></label>
          <div className="undo-wrapper" style={{ position: 'relative' }}>
            <button onClick={() => setValidatedText('')} className="fa-undo-button" style={{ borderRadius: '0%', zIndex: 0, background: 'transparent' }}>
              <FaUndo />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ValidateAddress;