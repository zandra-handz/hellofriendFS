import React, { useEffect, useState } from 'react';
import api from '../api';
import useAuthUser from '../hooks/UseAuthUser';
import Card from './DashboardStyling/Card';
import { FaFrown, FaStar, FaHeart, FaSmile, FaMeh, FaSadTear, FaThumbsDown } from 'react-icons/fa';
import useSelectedFriend from '../hooks/UseSelectedFriend';   

const FriendDaysSince = () => { 
  const [data, setData] = useState(null);
  const { authUser } = useAuthUser();
  const { selectedFriend } = useSelectedFriend();  

  const renderIcon = () => {
    switch (data.time_score) {
      case 1:
        return <FaHeart />;
      case 2:
        return <FaSmile />;
      case 3:
        return <FaFrown />;
      case 4:
        return <FaMeh />;
      case 5:
        return <FaFrown />;
      case 6:
        return <FaSadTear />;
      default:
        return null; 
    }
  };

  console.log('Selected Friend in FriendDaysSince:', selectedFriend);

  useEffect(() => {
    const fetchData = async () => {
      try {
        if (selectedFriend) {
          const response = await api.get(`/friends/${selectedFriend.id}/next-meet/`);

          console.log('Fetched Data:', response.data); 

          setData(response.data[0]);
        }
      } catch (error) {
        console.error('Error fetching data:', error);
      }
    };

    fetchData();
  }, [authUser, selectedFriend]);

  console.log('Current Data:', data); // Log the current data

  if (!selectedFriend) {
    // If no friend is selected, don't render anything
    return null;
  }

  return ( 
    <Card title="Days Since">
      {data && (
        <div>
          <p>{data.days_since} {renderIcon()} </p>
        </div>
      )}
    </Card> 
  );
};

export default FriendDaysSince;