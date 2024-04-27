import React, { useEffect, useState } from 'react';
import api from '../api';
import CardExpandAndConfig from './DashboardStyling/CardExpandAndConfig';
import Spinner from './DashboardStyling/Spinner';
import useAuthUser from '../hooks/UseAuthUser';
import useSelectedFriend from '../hooks/UseSelectedFriend'; 

const FriendSuggestionSettings = () => {
  const [data, setData] = useState(null);
  const [isEditMode, setIsEditMode] = useState(false);
  const [effortRequired, setEffortRequired] = useState('');
  const [priorityLevel, setPriorityLevel] = useState('');
  const [maxCategories, setMaxCategories] = useState('');
  const { authUser } = useAuthUser();
  const { selectedFriend } = useSelectedFriend();

  useEffect(() => {
    const fetchData = async () => {
      try {
        if (selectedFriend) {
          const response = await api.get(`/friends/${selectedFriend.id}/settings/`);
          setData(response.data);
          setEffortRequired(response.data.effort_required);
          setPriorityLevel(response.data.priority_level);
          setMaxCategories(response.data.category_limit_formula);
        }
      } catch (error) {
        console.error('Error fetching data:', error);
      }
    };
    fetchData();
  }, [selectedFriend]);

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
      fetchData();
    } catch (error) {
      console.error('Error updating settings:', error);
    }
  };

  return (
    <CardExpandAndConfig title="Friend Settings" onEditButtonClick={toggleEditMode}>
      {isEditMode ? (
        <div>
          <div>
            <h1>Effort:</h1>
            <input type="range" name="effort" min="1" max="5" value={effortRequired} onChange={handleInputChange} />
            <span>{effortRequired}</span>
          </div>
          <div>
            <h1>Priority:</h1>
            <input type="range" name="priority" min="1" max="3" value={priorityLevel} onChange={handleInputChange} />
            <span>{priorityLevel}</span>
          </div>
          <div>
            <button onClick={handleSubmit}>Submit</button>
          </div>
        </div>
      ) : (
        <div>
          {data ? (
            <div>
              <p><h1>Effort:</h1> {effortRequired}</p>
              <p><h1>Priority:</h1> {priorityLevel}</p>
              <p><h1>Max categories:</h1> {maxCategories}</p>
            </div>
          ) : (
            <Spinner />
          )}
        </div>
      )}
    </CardExpandAndConfig>
  );
};

export default FriendSuggestionSettings;
