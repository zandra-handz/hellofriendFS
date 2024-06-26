import React, { useEffect, useState } from 'react';
import api from '../api';
import CardExpandAndConfig from './DashboardStyling/CardExpandAndConfig';
import FormFriendFaves from './Forms/FormFriendFaves';
import Spinner from './DashboardStyling/Spinner';
import useAuthUser from '../hooks/UseAuthUser';
import useSelectedFriend from '../hooks/UseSelectedFriend';
import { FaWrench } from 'react-icons/fa';

const FriendFaves = () => {
  const [data, setData] = useState(null);
  const [expanded, setExpanded] = useState(false); // State to manage expanded/collapsed state
  const [isEditMode, setIsEditMode] = useState(false);
  const { selectedFriend, friendDashboardData, updateFriendDashboardData } = useSelectedFriend();

  useEffect(() => {
    const fetchData = async () => {
      try {
        if (friendDashboardData && friendDashboardData.length > 0) {
          const friendFaves = friendDashboardData[0].friend_faves;
          if (friendFaves) {
            setData(friendFaves);
          }
        }
      } catch (error) {
        console.error('Error fetching data:', error);
      }
    };

    fetchData();
  }, [friendDashboardData]);

  const toggleExpand = () => {
    setExpanded(prevExpanded => !prevExpanded);
  };

  const toggleEditMode = () => {
    setIsEditMode(prevMode => !prevMode);
  };

  const handleSubmit = async (updatedData) => {
    try {
      // Update friend faves settings
      await api.put(`/friends/${selectedFriend.id}/faves/update/`, updatedData);

      // Fetch updated dashboard data
      const dashboardResponse = await api.get(`/friends/${selectedFriend.id}/dashboard/`);
      const updatedDashboardData = dashboardResponse.data;

      // Update dashboard data
      updateFriendDashboardData(updatedDashboardData);

      setIsEditMode(false);
    } catch (error) {
      console.error('Error updating settings:', error);
    }
  };

  if (!selectedFriend) {
    return <p>No friend selected.</p>;
  }

  return (
    <CardExpandAndConfig title="Friend Favez" expanded={expanded} onCardExpandClick={toggleExpand}>
      <div className="edit-card-content">
        {expanded ? (
          <>
            <div className="edit-card-header" onClick={toggleEditMode}>
              <h5>Friend Faves</h5>
              <button className="edit-button">
                <FaWrench />
              </button>
            </div>
            {isEditMode ? (
              <div>
                {/* Edit mode content */}
                <FormFriendFaves locations={data.locations} handleSubmit={handleSubmit} />
              </div>
            ) : (
              <div>
                {/* View mode content */}
                {data ? (
                  <div>
                    <h1>Locations:</h1>
                    <select>
                      {data.locations.map(location => (
                        <option key={location.id} value={location.id}>{location.name}</option>
                      ))}
                    </select>
                  </div>
                ) : (
                  <Spinner />
                )}
              </div>
            )}
          </>
        ) : (
          <div>
            {/* Collapsed mode content */}
            <h1>Friend Faves</h1>
            {/* Place your non-editable content here */}
          </div>
        )}
      </div>
    </CardExpandAndConfig>
  );
};

export default FriendFaves;
