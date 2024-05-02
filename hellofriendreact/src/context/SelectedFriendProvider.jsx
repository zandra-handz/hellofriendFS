import React, { createContext, useState, useEffect } from 'react';
import api from '../api';

const SelectedFriendContext = createContext({});

export const SelectedFriendProvider = ({ children }) => {
  const [selectedFriend, setSelectedFriend] = useState(null);
  const [friendList, setFriendList] = useState([]);
  const [friendDashboardData, setFriendDashboardData] = useState(null);
  const [loadingNewFriend, setLoadingNewFriend] = useState(false); // New state for loading new friend data

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
        setLoadingNewFriend(true); // Set loading state to true when fetching data for a new friend
        try {
          // Fetch friend dashboard data based on selected friend
          const dashboardResponse = await api.get(`/friends/${selectedFriend.id}/dashboard/`);
          const dashboardData = dashboardResponse.data;
          console.log('Friend dashboard data:', dashboardData); // Log the dashboard data
          setFriendDashboardData(dashboardData);
        } catch (error) {
          console.error('Error fetching friend dashboard data:', error);
        } finally {
          setLoadingNewFriend(false); // Set loading state to false when data fetching is complete
        }
      } else {
        // If no friend is selected, clear the dashboard data
        setFriendDashboardData(null);
      }
    };

    fetchFriendDashboard();
  }, [selectedFriend]);

  // Log what is being passed into setFriend
  useEffect(() => {
    console.log('Selected friend being set:', selectedFriend);
  }, [selectedFriend]);

  return (
    <SelectedFriendContext.Provider value={{ selectedFriend, setFriend: setSelectedFriend, friendList, friendDashboardData, loadingNewFriend }}>
      {children}
    </SelectedFriendContext.Provider>
  );
};

export default SelectedFriendContext;
