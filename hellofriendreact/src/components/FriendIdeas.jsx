import React, { useEffect, useState } from 'react';
import api from '../api';
import CardUneditable from './DashboardStyling/CardUneditable';
import useAuthUser from '../hooks/UseAuthUser';
import useSelectedFriend from '../hooks/UseSelectedFriend';
import useThemeMode from '/src/hooks/UseThemeMode';

const FriendIdeas = () => {
  const { themeMode } = useThemeMode();
  const [thoughtCapsules, setThoughtCapsules] = useState([]);
  const [categoryData, setCategoryData] = useState({});
  const { authUser } = useAuthUser();
  const { selectedFriend } = useSelectedFriend();

  useEffect(() => {
    const fetchData = async () => {
      try {
        if (selectedFriend) {
          // Fetch thought capsules
          const thoughtCapsulesResponse = await api.get(`/friends/${selectedFriend.id}/thoughtcapsules/`);
          setThoughtCapsules(thoughtCapsulesResponse.data);

          // Fetch category data
          const categoryDataResponse = await api.get(`/friends/${selectedFriend.id}/next-meet/`);
          setCategoryData(categoryDataResponse.data[0]);
        }
      } catch (error) {
        console.error('Error fetching data:', error);
      }
    };

    fetchData();
  }, [authUser, selectedFriend]);

  return (
    <div>
      {Object.keys(categoryData).length > 0 ? (
        Object.entries(categoryData.thought_capsules_by_category).map(([category, capsules]) => (
          <div key={category}>
            <CardUneditable title={category}>
              {capsules.map((capsule) => (
                <>
                <p key={capsule.id}>○ {capsule.capsule}</p>
               </>
              ))}
            </CardUneditable>
          </div>
        ))
      ) : (
        <p></p>
      )}
    </div>
  );
};

export default FriendIdeas;
