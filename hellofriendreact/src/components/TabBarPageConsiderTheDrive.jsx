import React, { useState, useEffect } from 'react';
import api from '../api/';
import Card from './DashboardStyling/Card';
import CardPlaces from './DashboardStyling/CardPlaces';
import CardPlacesSetSearch from './DashboardStyling/CardPlacesSetSearch';
import ValidateAddress from './ValidateAddress';
import useSelectedFriend from '../hooks/UseSelectedFriend';
import useAuthUser from '../hooks/UseAuthUser';
import useThemeMode from '../hooks/UseThemeMode';
import '/src/styles/OldStyles.css';
import { FaRoad } from 'react-icons/fa';

const TabBarPageConsiderTheDrive = () => {
  const { themeMode } = useThemeMode();
  const { authUser } = useAuthUser();

  const [addressA, setAddressA] = useState(null);
  const [addressB, setAddressB] = useState(null);
  const [destinationAddress, setDestinationAddress] = useState(null);
  const [searchKeyword, setSearchKeyword] = useState('restaurants');
  const [searchRadius, setSearchRadius] = useState(5000);
  const [searchLength, setSearchLength] = useState(8);
  const [performSearch, setPerformSearch] = useState(false);
  const [considerTheDriveData, setConsiderTheDriveData] = useState(null);
  const [redoMode, setRedoMode] = useState(true);
  const [loading, setLoading] = useState(false); // Track loading state 

  const { selectedFriend } = useSelectedFriend();



  const handleValidationChange = (isValid, address, latitude, longitude, addressKey) => {
    if (isValid) {
      if (addressKey === 'A') {
        setAddressA({ address, latitude, longitude });
      } else if (addressKey === 'B') {
        setAddressB({ address, latitude, longitude });
      } else if (addressKey === 'Destination') {
        setDestinationAddress({ address, latitude, longitude });
        setConsiderTheDriveData('');
      }
    } else {
      // Handle invalid address if needed
    }
  };

  const handleSubmit = async () => {
    setLoading(true); // Set loading to true when starting the API request
    if (addressA && addressB && destinationAddress) {
      try {
        const response = await api.post(`/friends/places/`, {
          address_a_address: addressA.address,
          address_a_lat: addressA.latitude,
          address_a_long: addressA.longitude,
          address_b_address: addressB.address,
          address_b_lat: addressB.latitude,
          address_b_long: addressB.longitude,
          destination_address: destinationAddress.address,
          destination_lat: destinationAddress.latitude,
          destination_long: destinationAddress.longitude,
          search: searchKeyword,
          radius: searchRadius,
          length: searchLength,
          perform_search: performSearch, // Use the state directly here
          user: { authUser }, // Replace 'user' with the actual user data
        });

        // Update the state with the response data
        setConsiderTheDriveData(response.data);
        setRedoMode(false);
        setLoading(false); // Set loading to false when response is received
        console.log('Consider the Drive Response:', response.data);
      } catch (error) {
        console.error('Error submitting addresses:', error);
        setLoading(false); // Set loading to false in case of error
      }
    } else {
      console.warn('Please enter and validate all addresses.');
      setLoading(false); // Set loading to false if addresses are not entered/validated
    }
  };

  useEffect(() => {
    // Function to handle changes in redoMode and update the content of the card
    const handleRedoModeChange = () => {
      // Logic to conditionally render content based on redoMode
      if (redoMode) {
        // Content for redoMode being true
        console.log("Redo Mode is True");
        // You can set or update state, or trigger any other necessary actions here
      } else {
        // Content for redoMode being false
        console.log("Redo Mode is False");
        // You can set or update state, or trigger any other necessary actions here
      }
    };

    // Call the function to handle initial rendering
    handleRedoModeChange();
  }, [redoMode]);

  const toggleRedoMode = () => {
    setRedoMode(prevRedoMode => !prevRedoMode);
  };


  return (
    <div>
      
      <CardPlacesSetSearch  
        showRedoButton={considerTheDriveData !== null} 
        onRedoButtonClick={toggleRedoMode} 
        isRedoMode={redoMode} // Pass the redoMode state
        buttonClassName="places-card-content-places-redo-button"
      >
        {redoMode && (
          <div className="places-card-content">
            <div className="places-restrictor">
              <div className="validate-address-container">
                <div className="places-card-indv">
                  <ValidateAddress headerText="My starting address: " onValidationChange={(isValid, address, lat, long) => handleValidationChange(isValid, address, lat, long, 'A')} />
                </div>
              </div>
              <div className="validate-address-container">
                <div className="places-card-indv">
                  <ValidateAddress headerText={`${selectedFriend.name}'s starting address: `} onValidationChange={(isValid, address, lat, long) => handleValidationChange(isValid, address, lat, long, 'B')} />
                </div>
              </div>
              <div className="validate-address-container">
                <div className="places-card-indv">
                  <ValidateAddress headerText="Going to: " onValidationChange={(isValid, address, lat, long) => handleValidationChange(isValid, address, lat, long, 'Destination')} />
                </div>
              </div>
            </div>
          </div>
        )}

        {redoMode && (
          <div className="places-card-content">
            <div className="places-restrictor-proximity-search">
              <div className="checkbox-section">
                <label>
                  Search for other places?
                  <input
                    type="checkbox"
                    checked={performSearch}
                    onChange={(e) => setPerformSearch(e.target.checked)}
                  />
                </label>
              </div>
              <div className="section">
                <label htmlFor="searchKeyword">Search: </label>
                <input
                  type="text"
                  id="searchKeyword"
                  value={searchKeyword}
                  onChange={(e) => setSearchKeyword(e.target.value)}
                  className="long-input"
                />
                <label htmlFor="searchRadius"> Radius: </label>
                <input
                  type="number"
                  id="searchRadius"
                  value={searchRadius}
                  onChange={(e) => {
                    const newValue = Math.min(Math.max(parseInt(e.target.value) || 1, 1), 5000); // Ensure the value is between 1 and 5000
                    setSearchRadius(newValue);
                  }}
                  className="short-input"
                  min="1"
                  max="5000"
                />
                <label htmlFor="searchLength">Results: </label>
                <input
                  type="number"
                  id="searchLength"
                  value={searchLength}
                  onChange={(e) => {
                    const newValue = Math.min(Math.max(parseInt(e.target.value) || 1, 1), 15);
                    setSearchLength(newValue);
                  }}
                  className="short-input"
                  min="1"
                  max="15"
                />
              </div>
            </div>
          </div>
        )}
        {redoMode && (
        <div className="places-card-content">
          <div className="places-restrictor">
            <button className="submit-button" onClick={handleSubmit} disabled={!addressA || !addressB || !destinationAddress}>
              {loading ? 'Loading...' : 'Get travel times' } <FaRoad /> {/* Change button text based on loading state */}
            </button>
          </div>
        </div>
        )}
        {!redoMode && considerTheDriveData && (
        <div className="travel-comparison-container">
          <div className="travel-comparison-container-header">
            {destinationAddress.address}
          </div>
          <div>
            <pre>Me: {String(considerTheDriveData.compare_directions.Me.duration)} {String(considerTheDriveData.compare_directions.Me.distance)}</pre>
          </div>
          <div> 
          <pre>{selectedFriend.name}: {String(considerTheDriveData.compare_directions.friend.duration)} {String(considerTheDriveData.compare_directions.friend.distance)}</pre>
          </div>
        </div>
          )} 

      </CardPlacesSetSearch>
      {!redoMode && considerTheDriveData && considerTheDriveData.suggested_places && (
        <div>
          {considerTheDriveData.suggested_places.map((place, index) => (
            <Card key={index}>
              <div>
                <h3>{place.name}</h3>
                <p>{place.address}</p>
                <p>
                  {place.formatted_phone_number} | {place.website && (
                    <a href={place.website} target="_blank" rel="noopener noreferrer">
                      More info
                    </a>
                  )}
                </p>
                <p>{place.opening_hours}</p>
                {place.distances.map((distance, distanceIndex) => (
                  <div key={distanceIndex}>
                    <p>
                      {Object.keys(distance)[0]}: {place.travel_times[distanceIndex][Object.keys(distance)[0]]} (
                      {distance[Object.keys(distance)[0]].toFixed(1)} mi)
                    </p>
                  </div>
                ))}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

export default TabBarPageConsiderTheDrive;