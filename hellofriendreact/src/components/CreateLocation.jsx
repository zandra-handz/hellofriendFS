import React, { useState } from 'react';
import api from '../api';  
import CardCreate from './DashboardStyling/CardCreate';
import CreateLocationForm from './CreateLocationForm'; 

const CreateLocation = () => {
  const [isFormVisible, setIsFormVisible] = useState(false); // State to manage form visibility

  const toggleFormVisibility = () => {
    setIsFormVisible(prevState => !prevState);
  };

  return (
    <CardCreate title="Add Location" onClick={toggleFormVisibility}>
      {isFormVisible && <CreateLocationForm />}
    </CardCreate>
  );
};

export default CreateLocation;
