import React, { useState, useEffect } from 'react';
import api from '../api';
import { FaCheck } from 'react-icons/fa';
import useAuthUser from '/src/hooks/UseAuthUser';
import useSelectedFriend from '/src/hooks/UseSelectedFriend';
import useThemeMode from '../hooks/UseThemeMode';

const ValidateFriendAddress = ({ onValidationChange }) => {
  const { themeMode } = useThemeMode();
  const [selectedAddress, setSelectedAddress] = useState('');
  const [inputAddress, setInputAddress] = useState('');
  const [savedAddresses, setSavedAddresses] = useState([]);
  const { authUser } = useAuthUser();
  const { selectedFriend } = useSelectedFriend();

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await api.get(`/friends/dropdown/validated-user-locations/`);
        setSavedAddresses(response.data);
      } catch (error) {
        console.error('Error fetching data:', error);
      }
    };

    fetchData(); // Fetch saved addresses when the component mounts
  }, []); // Empty dependency array means this effect runs only once when the component mounts

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
      const selectedOption = savedAddresses.find(address => address.address === value);
      if (selectedOption) {
        const { address, latitude, longitude } = selectedOption;
        // Trigger validation and notify parent component
        onValidationChange(true, address, latitude, longitude);
      }
    }
  };

  const handleInputChange = (e) => {
    const value = e.target.value;
    setInputAddress(value);
    // Clear selected address when input changes
    setSelectedAddress('');
  };

  return (
    <div>
      <select value={selectedAddress} onChange={handleSelectChange}>
        <option value="">Select saved address</option>
        {savedAddresses.map(address => (
          <option key={address.id} value={address.address}>{address.address}</option>
        ))}
      </select>
      <button onClick={handleValidation}><FaCheck /></button>
      <input
        type="text"
        placeholder="Enter address"
        value={inputAddress}
        onChange={handleInputChange}
      />
    </div>
  );
};

export default ValidateFriendAddress;
