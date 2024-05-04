import React, { useEffect, useState } from 'react';
import api from '../api';
import CardExpandAndConfig from './DashboardStyling/CardExpandAndConfig';
import Spinner from './DashboardStyling/Spinner';
import useAuthUser from '../hooks/UseAuthUser';
import useSelectedFriend from '../hooks/UseSelectedFriend';
import FormFriendInfo from './Forms/FormFriendInfo'; // Import the FriendInfoForm component
import { FaWrench } from 'react-icons/fa';


const FriendInfo = () => {
  const [friendData, setFriendData] = useState(null);
  const [isEditMode, setIsEditMode] = useState(false);
  const [expanded, setExpanded] = useState(false); // State for managing expanded/collapsed state
  const { authUser } = useAuthUser();
  const { selectedFriend, friendDashboardData, updateFriendDashboardData } = useSelectedFriend();

  useEffect(() => {
    const updateFriendInfo = () => {
      if (friendDashboardData && friendDashboardData.length > 0) {
        const friend = friendDashboardData[0];
        setFriendData({
          user: authUser.user.id, 
          name: friend.name,
          first_name: friend.first_name,
          last_name: friend.last_name,
          first_meet_entered: friend.first_meet_entered,
        });
      }
    };

    updateFriendInfo();
  }, [friendDashboardData]);

  const toggleEditMode = () => {
    setIsEditMode(prevMode => !prevMode);
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFriendData({ ...friendData, [name]: value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault(); // Prevent form submission's default behavior
    try {
      // Perform API call to update friend-specific fields
      await api.put(`/friends/${selectedFriend.id}/info/`, friendData);

      // Fetch updated dashboard data (optional)
      const dashboardResponse = await api.get(`/friends/${selectedFriend.id}/dashboard/`);
      const updatedDashboardData = dashboardResponse.data;

      // Update dashboard data (optional)
      updateFriendDashboardData(updatedDashboardData);

      setIsEditMode(false);
    } catch (error) {
      console.error('Error updating friend info:', error);
    }
  };


  return (
    <CardExpandAndConfig
      title="Friend Info"
      expanded={expanded}
      onCardExpandClick={() => setExpanded(prevExpanded => !prevExpanded)}
    >
      <>
        {expanded ? (
          <div>
            <div className="edit-card-header" onClick={toggleEditMode}>
              <h5>Friend Info</h5>
              <button className="edit-button">
                <FaWrench />
              </button>
            </div>
            {isEditMode ? (
              // Render form for editing
              <FormFriendInfo
                friendData={friendData}
                handleInputChange={handleInputChange}
                handleSubmit={handleSubmit}
              />
            ) : (
              // Render friend data
              friendData ? (
                <>
                  <p>Name: {friendData.name}</p>
                  <p>First Name: {friendData.first_name}</p>
                  <p>Last Name: {friendData.last_name}</p>
                  <p>First Date Entered: {friendData.first_meet_entered}</p>
                </>
              ) : (
                <Spinner />
              )
            )}
           
          </div>
        ) : (
          <div>
            <h5>Friend Info</h5>
            {friendData ? (
              <>
                <p>Name: {friendData.name}</p>
                <p>First Name: {friendData.first_name}</p>
              </>
            ) : (
              <Spinner />
            )}
          </div>
        )}
      </>
    </CardExpandAndConfig>
  );
};

export default FriendInfo;