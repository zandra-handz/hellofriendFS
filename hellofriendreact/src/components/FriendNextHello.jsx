import React from 'react';
import Card from './DashboardStyling/Card';
import useSelectedFriend from '../hooks/UseSelectedFriend';   

const FriendNextHello = () => { 
  const { friendDashboardData } = useSelectedFriend();  

  // Check if friendDashboardData is not null and has at least one element
  if (!friendDashboardData || friendDashboardData.length === 0) {
    // Return null or some placeholder component if there's no data
    return null; // or return <p>No data available</p>;
  }

  const firstFriendData = friendDashboardData[0]; // Assuming you want data for the first friend

  return ( 
    <Card title="Next Meetup">
      <p>{firstFriendData.future_date_in_words} </p>
    </Card> 
  );
};

export default FriendNextHello;
