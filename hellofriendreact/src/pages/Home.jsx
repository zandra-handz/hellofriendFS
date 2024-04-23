// Home.jsx
import React, { useState, useEffect } from 'react';
import api from '../api';
import TabBar from '../components/DashboardStyling/TabBar';
import Tab from '../components/DashboardStyling/Tab';
import Header from '../components/DashboardStyling/Header';
import NextHelloes from '../components/NextHelloes';
import FriendDaysSince from '../components/FriendDaysSince';
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
  const { selectedFriend } = useSelectedFriend();  
  const { focusMode } = useFocusMode();

  return (
    <div className="App">
      <Header />
      
      {/* <FriendSelectorContainer /> */}
      
      <TabBar>
      {!selectedFriend && (
        <Tab label="Home">
            <NextHelloes />
        </Tab>
      )}
        
      {selectedFriend && !focusMode && (
        <Tab label="Dash">
            <FriendDaysSince />
            <FriendFaves />
            <FriendSuggestionSettings />
        </Tab>
      )}

      {selectedFriend && (
        <Tab label="Thoughts">
          <FriendIdeas />
          <FriendImages />
        </Tab>
      )}
      {selectedFriend && (
        <Tab label="Places">
          <TabBarPageConsiderTheDrive />
        </Tab>
      )}
      {selectedFriend && !focusMode && (
        <Tab label="Past meetups">
          <TabBarPageHelloes />
        </Tab>
      )}


      {!selectedFriend && (
        <Tab label="Friends"> 
          <TabBarPageUserFriendsAll />
        </Tab>
      )}
      {!selectedFriend && (
        <Tab label="Locations"> 
          <TabBarPageUserLocationsAll />
        
        </Tab>
      )}
      {!selectedFriend && (
        <Tab label="Settings"> 
          <UserSettings />
          <UserProfile />
        </Tab>
      )}
        
      
      </TabBar>
    </div>
  );
};

export default Home;

           

