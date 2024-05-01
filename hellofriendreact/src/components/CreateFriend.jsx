import React, { useState } from 'react'; 
import CardCreate from './DashboardStyling/CardCreate';
import CreateFriendForm from './CreateFriendForm'; 

const CreateFriend = () => {
  const [isFormVisible, setIsFormVisible] = useState(false); // State to manage form visibility

  const toggleFormVisibility = () => {
    setIsFormVisible(prevState => !prevState);
  };

  return (
    <CardCreate title="Add Friend" onClick={toggleFormVisibility}>
      {isFormVisible && <CreateFriendForm />}
    </CardCreate>
  );
};

export default CreateFriend;
