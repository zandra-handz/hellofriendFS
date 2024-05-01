import React, { useState } from 'react';
import CardCreate from './DashboardStyling/CardCreate';
import FormLocationCreate from './Forms/FormLocationCreate';


import MessageSave from './DashboardStyling/MessageSave'; // Import the MessageSave component

const CreateLocation = ({ onLocationCreate }) => {
  const [isFormVisible, setIsFormVisible] = useState(false); // State to manage form visibility
  const [showSaveMessage, setShowSaveMessage] = useState(false); // State to manage save message visibility

  const toggleFormVisibility = () => {
    setIsFormVisible(prevState => !prevState);
  };

  const handleLocationCreate = async (newLocation) => {
    onLocationCreate(newLocation); // Call the callback function to add the new location
    setShowSaveMessage(true); // Show the save message

    setTimeout(() => {
      setShowSaveMessage(false); // Hide the save message after 3 seconds
      
    }, 3000);
  };

  const handleSaveMessageClose = () => {
    setShowSaveMessage(false); // Hide the save message
    setIsFormVisible(false); 
  };

  return (
    <CardCreate title="Add Location" onClick={toggleFormVisibility}>
      {showSaveMessage && <MessageSave sentenceObject={{ message: 'Location created successfully!' }} onClose={handleSaveMessageClose} />} 
      {isFormVisible && <FormLocationCreate onLocationCreate={handleLocationCreate} />} 
    </CardCreate>
  );
};

export default CreateLocation;
