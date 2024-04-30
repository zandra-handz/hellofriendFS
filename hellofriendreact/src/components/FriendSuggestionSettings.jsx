// FriendSuggestionSettings.jsx
import React, { useEffect, useState } from 'react';
import api from '../api';
import CardExpandAndConfigSliders from './DashboardStyling/CardExpandAndConfigSliders';
import FormFriendSettings from './Forms/FormFriendSettings';
import Spinner from './DashboardStyling/Spinner';
import useAuthUser from '../hooks/UseAuthUser';
import useSelectedFriend from '../hooks/UseSelectedFriend';
import { FaWrench } from 'react-icons/fa';

const FriendSuggestionSettings = () => {
  const [data, setData] = useState(null);
  const [isEditMode, setIsEditMode] = useState(false);
  const [effortRequired, setEffortRequired] = useState('');
  const [priorityLevel, setPriorityLevel] = useState('');
  const [expanded, setExpanded] = useState(false); // State for managing expanded/collapsed state
  const { authUser } = useAuthUser();
  const { selectedFriend, friendDashboardData } = useSelectedFriend();

  useEffect(() => {
    const fetchData = async () => {
      try {
        if (friendDashboardData && friendDashboardData.length > 0) {
          const suggestionSettings = friendDashboardData[0].suggestion_settings;
          if (suggestionSettings) {
            setData(suggestionSettings);
            setEffortRequired(suggestionSettings.effort_required);
            setPriorityLevel(suggestionSettings.priority_level);
          }
        }
      } catch (error) {
        console.error('Error fetching data:', error);
      }
    };
    fetchData();
  }, [friendDashboardData]);

  const toggleEditMode = () => {
    setIsEditMode(prevMode => !prevMode);
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    switch (name) {
      case 'effort':
        if (['1', '2', '3', '4', '5'].includes(value)) {
          setEffortRequired(value);
        }
        break;
      case 'priority':
        if (['1', '2', '3'].includes(value)) {
          setPriorityLevel(value);
        }
        break;
      default:
        break;
    }
  };

  const handleSubmit = async () => {
    try {
      await api.put(`/friends/${selectedFriend.id}/settings/update/`, {
        user: authUser.user.id,
        friend: selectedFriend.id,
        effort_required: effortRequired,
        priority_level: priorityLevel
      });
      setIsEditMode(false);
    } catch (error) {
      console.error('Error updating settings:', error);
    }
  };

  if (!selectedFriend) {
    return <p>No friend selected.</p>;
  }

  return (
    <CardExpandAndConfigSliders title="Friend Settings" expanded={expanded} onEditButtonClick={() => setExpanded(prevExpanded => !prevExpanded)}>
      <>
        {expanded ? (
          <>
            <div className="edit-card-header" onClick={toggleEditMode}>
              <h5>Friend Settings</h5>
              <button className="edit-button">
                <FaWrench />
              </button>
            </div>
            {isEditMode ? (
              <FormFriendSettings
                effortRequired={effortRequired}
                priorityLevel={priorityLevel}
                handleInputChange={handleInputChange}
                handleSubmit={handleSubmit}
              />
            ) : (
              <div>
                <h6>Effort Required: {effortRequired}</h6>
                <h6>Priority Level: {priorityLevel}</h6>
              </div>
            )}
          </>
        ) : (
          <div>
            <h5>Friend Settings</h5>
            {data ? (
              <>
                <p>Effort Required: {data.effort_required}</p>
                <p>Priority Level: {data.priority_level}</p>
              </>
            ) : (
              <Spinner />
            )}
          </div>
        )}
      </>
    </CardExpandAndConfigSliders>
  );
};

export default FriendSuggestionSettings;
