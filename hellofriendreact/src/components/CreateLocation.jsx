import React, { useState } from 'react';
import CardCreate from './DashboardStyling/CardCreate';
import FormLocationCreate from './Forms/FormLocationCreate';
import MessageSave from './DashboardStyling/MessageSave'; 
import useLocationList from '../hooks/UseLocationList'; 

const CreateLocation = () => {
  const { locationList, setLocationList } = useLocationList();
  const [isFormVisible, setIsFormVisible] = useState(false);
  const [showSaveMessage, setShowSaveMessage] = useState(false);

  const toggleFormVisibility = () => {
    setIsFormVisible(prevState => !prevState);
  };

  const handleLocationCreate = async (newLocation) => {
    try {
      // Update locationList state by adding the new location
      setLocationList(prevLocationList => [...prevLocationList, newLocation]);
      setShowSaveMessage(true); // Show the save message

      setTimeout(() => {
        setShowSaveMessage(false); // Hide the save message after 3 seconds
      }, 3000);
    } catch (error) {
      console.error('Error creating location:', error);
    }
  };

  const handleSaveMessageClose = () => {
    setShowSaveMessage(false); // Hide the save message
    setIsFormVisible(false);
  };

  return (
    <div>
      <CardCreate title="Add Location" onClick={toggleFormVisibility}>
        {showSaveMessage && <MessageSave sentenceObject={{ message: 'Location created successfully!' }} onClose={handleSaveMessageClose} />}
        {isFormVisible && <FormLocationCreate onLocationCreate={handleLocationCreate} />} 
      </CardCreate>
    </div>
  );
};

export default CreateLocation;
