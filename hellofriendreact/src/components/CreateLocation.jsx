import React, { useState } from 'react';
import CardCreate from './DashboardStyling/CardCreate';
import FormLocationCreate from './Forms/FormLocationCreate';

const CreateLocation = () => {
  const [isFormVisible, setIsFormVisible] = useState(false); // State to manage form visibility

  const toggleFormVisibility = () => {
    setIsFormVisible(prevState => !prevState);
  };

  return (
    <CardCreate title="Add Location" onClick={toggleFormVisibility}>
      {isFormVisible && <FormLocationCreate />}
    </CardCreate>
  );
};

export default CreateLocation;
