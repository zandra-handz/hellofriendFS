import React, { useEffect, useState } from 'react';
import api from '../api';
import CardExpandAndConfig from './DashboardStyling/CardExpandAndConfig';
import Spinner from './DashboardStyling/Spinner';
import useAuthUser from '../hooks/UseAuthUser';
import useSelectedFriend from '../hooks/UseSelectedFriend'; 

const FriendFaves = () => {
  const [data, setData] = useState(null);
  const { authUser } = useAuthUser();
  const { selectedFriend, friendDashboardData } = useSelectedFriend();

  useEffect(() => {
    const fetchData = async () => {
      try {
        if (friendDashboardData && friendDashboardData.length > 0) {
          // Assuming friend_faves is nested inside friendDashboardData
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

  if (!selectedFriend) {
    return <p>No friend selected.</p>;
  }

  return (
    <CardExpandAndConfig title="Friend Favez">
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
        <p></p>
      )}
    </CardExpandAndConfig>
  );
};

export default FriendFaves;
