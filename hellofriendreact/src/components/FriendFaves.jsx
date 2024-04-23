

import React, { useEffect, useState } from 'react';
import api from '../api';
import EditCard from './DashboardStyling/EditCard';
import useAuthUser from '../hooks/UseAuthUser';
import useSelectedFriend from '../hooks/UseSelectedFriend';

const FriendFaves = () => {
  const [data, setData] = useState(null);
  const { authUser } = useAuthUser();
  const { selectedFriend } = useSelectedFriend();

  useEffect(() => {
    const fetchData = async () => {
      try {
        if (selectedFriend) {
          const response = await api.get(`/friends/${selectedFriend.id}/faves/`);

          setData(response.data);
        }
      } catch (error) {
        console.error('Error fetching data:', error);
      }
    };

    fetchData();
  }, [authUser, selectedFriend]);

  if (!selectedFriend) {
    return <p>No friend selected.</p>;
  }

  return (
    <EditCard title="Friend Favez">
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
        <p>Loading...</p>
    )}
    </EditCard>
  );
};

export default FriendFaves;