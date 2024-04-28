import React from 'react';
import CardHalfWidth from './DashboardStyling/CardHalfWidth';
import { FaFrown, FaStar, FaHeart, FaSmile, FaMeh, FaSadTear, FaThumbsDown } from 'react-icons/fa';
import useSelectedFriend from '../hooks/UseSelectedFriend';   

const FriendDaysSince = () => { 
  const { friendDashboardData } = useSelectedFriend();  

  const renderIcon = () => {
    if (!friendDashboardData || !friendDashboardData.length) return null; // Check if dashboard data exists and is not empty

    const firstFriendData = friendDashboardData[0]; // Assuming you want data for the first friend
    switch (firstFriendData.time_score) {
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

  if (!friendDashboardData || !friendDashboardData.length) {
    // If no dashboard data is available, don't render anything
    return null;
  }

  const firstFriendData = friendDashboardData[0]; // Assuming you want data for the first friend

  return ( 
    <>
      <h4>Days Since: </h4>
      <h4>{firstFriendData.days_since}   {renderIcon()}</h4>
    </>
    
  );
};

export default FriendDaysSince;
