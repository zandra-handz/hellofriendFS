// Home.jsx
import React, { useState, useEffect } from 'react';
import api from '../api';
import TabBar from '../components/DashboardStyling/TabBar';
import Tab from '../components/DashboardStyling/Tab';
import Header from '../components/DashboardStyling/Header';
import TabSpinner from '../components/DashboardStyling/TabSpinner';
import NextHelloes from '../components/NextHelloes';
import FriendDashHeader from '../components/FriendDashHeader';
import FriendDaysSince from '../components/FriendDaysSince';
import FriendNextHello from '../components/FriendNextHello';
import FriendIdeas from '../components/FriendIdeas';
import FriendImages from '../components/FriendImages';
import UserSettings from '../components/UserSettings';
import UserProfile from '../components/UserProfile';
import TabBarPageHelloes from '../components/TabBarPageHelloes';
import TabBarPageConsiderTheDrive from '../components/TabBarPageConsiderTheDrive';
import ThoughtCapsules from '../components/ThoughtCapsules'; // Import ThoughtCapsules component
import AddThoughtCapsule from '../components/AddThoughtCapsule'; // Import AddThoughtCapsule component
import FriendSuggestionSettings from '../components/FriendSuggestionSettings';
import FriendFaves from '../components/FriendFaves';
import useAuthUser from '../hooks/UseAuthUser';
import useSelectedFriend from '../hooks/UseSelectedFriend';
import useFocusMode from '../hooks/UseFocusMode';
import useThemeMode from '../hooks/UseThemeMode';
import TabBarPageUserLocationsAll from '../components/TabBarPageUserLocationsAll';
import TabBarPageUserFriendsAll from '../components/TabBarPageUserFriendsAll';


const Home = () => {
  const { themeMode } = useThemeMode();
  const { selectedFriend, loadingNewFriend } = useSelectedFriend(); // Accessing selected friend and friend dashboard data
  const { focusMode } = useFocusMode();
  const [loading, setLoading] = useState(true); 

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Simulate API call delay
        await new Promise(resolve => setTimeout(resolve, 2000));
        setLoading(false); // Set loading to false when data fetching is complete
      } catch (error) {
        console.error('Error fetching data:', error);
        setLoading(false); // Set loading to false in case of error
      }
    };

    fetchData();
  }, []); // Empty dependency array to run once when component mounts

  return (
    <div className="App">
      <Header />
      
      {/* <FriendSelectorContainer /> */}
      
      <TabBar>
        {!selectedFriend && (
          <Tab label="Home">
            {loading ? (
              <TabSpinner />
            ) : (
              <NextHelloes />
            )}
          </Tab>
        )}
  
        {selectedFriend && !focusMode && (
          <Tab label="Dash">
            {loadingNewFriend ? (
              <TabSpinner />
            ) : (
              <>
                <FriendDashHeader
                  friendDaysSince={<FriendDaysSince />}
                  friendNextHello={<FriendNextHello />}
                />
                <FriendFaves />
                <FriendSuggestionSettings />
              </>
            )}
          </Tab>
        )}
  
        {selectedFriend && (
          <Tab label="Thoughts">
            {loadingNewFriend ? (
              <TabSpinner />
            ) : (
              <>
                <FriendIdeas />
                <FriendImages />
              </>
            )}
          </Tab>
        )}
  
        {selectedFriend && (
          <Tab label="Places">
            {loadingNewFriend ? (
              <TabSpinner />
            ) : (
              <TabBarPageConsiderTheDrive />
            )}
          </Tab>
        )}
  
        {selectedFriend && !focusMode && (
          <Tab label="Meetups">
            {loadingNewFriend ? (
              <TabSpinner />
            ) : (
              <TabBarPageHelloes />
            )}
          </Tab>
        )}
  
        {!selectedFriend && (
          <Tab label="Friends"> 
            {loadingNewFriend ? (
              <TabSpinner />
            ) : (
              <TabBarPageUserFriendsAll />
            )}
          </Tab>
        )}
  
        {!selectedFriend && (
          <Tab label="Locations"> 
            {loadingNewFriend ? (
              <TabSpinner />
            ) : (
              <TabBarPageUserLocationsAll />
            )}
          </Tab>
        )}
  
        {!selectedFriend && (
          <Tab label="Settings"> 
            {loadingNewFriend ? (
              <TabSpinner />
            ) : (
              <>
                <UserSettings />
                <UserProfile />
              </>
            )}
          </Tab>
        )}
      </TabBar>
    </div>
  );
  
};

export default Home;

           

