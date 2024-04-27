// SelectedFriendProvider.jsx
import React, { createContext, useState, useEffect } from 'react';
import api from '../api';

const SelectedFriendContext = createContext({});

export const SelectedFriendProvider = ({ children }) => {
  const [selectedFriend, setSelectedFriend] = useState(null);
  const [friendList, setFriendList] = useState([]);
  const [friendDashboardData, setFriendDashboardData] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch all friends
        const friendResponse = await api.get('/friends/all/');
        const friendData = friendResponse.data;
        setFriendList(friendData);

        // Initially, no friend is selected
        setSelectedFriend(null);
      } catch (error) {
        console.error('Error fetching friend data:', error);
      }
    };

    fetchData();
  }, []);

  useEffect(() => {
    const fetchFriendDashboard = async () => {
      if (selectedFriend) {
        try {
          // Fetch friend dashboard data based on selected friend
          const dashboardResponse = await api.get(`/friends/${selectedFriend.id}/dashboard/`);
          const dashboardData = dashboardResponse.data;
          console.log('Friend dashboard data:', dashboardData); // Log the dashboard data
          setFriendDashboardData(dashboardData);
        } catch (error) {
          console.error('Error fetching friend dashboard data:', error);
        }
      } else {
        // If no friend is selected, clear the dashboard data
        setFriendDashboardData(null);
      }
    };

    fetchFriendDashboard();
  }, [selectedFriend]);

  return (
    <SelectedFriendContext.Provider value={{ selectedFriend, setFriend: setSelectedFriend, friendList, friendDashboardData }}>
      {children}
    </SelectedFriendContext.Provider>
  );
};

export default SelectedFriendContext;
