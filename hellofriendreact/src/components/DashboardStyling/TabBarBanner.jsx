import React from 'react';
import FriendSelector from '../FriendSelector';
import QuickButtons from './QuickButtons';
import ToggleFriendFocus from './ToggleFriendFocus';
import AddHelloButton from './AddHelloButton';
import AddSShotsMemesButton from './AddSShotsMemesButton';
import useSelectedFriend from '/src/hooks/UseSelectedFriend'; 
import '/src/styles/OldStyles.css';
import useThemeMode from '/src/hooks/UseThemeMode';
import useFocusMode from '/src/hooks/UseFocusMode';

const TabBarBanner = () => {
  const { themeMode } = useThemeMode();
  const { focusMode } = useFocusMode();
  const { selectedFriend } = useSelectedFriend();

  return (
    <div className={`${themeMode === 'dark' ? 'dark-mode' : ''}`}>
      <div className="banner">
        <div className="banner-content"> 

          <div className="banner-text-field-container-friend-selector">
            <div>
              <FriendSelector />
            </div>
          </div>
 
          
          {selectedFriend && !focusMode && (
            <div className="banner-text-field-container">
              <QuickButtons buttonClassName="banner-button-first" /> 
            </div>
          )}
          </div>
          <div className="banner-text-field-container">

          {selectedFriend && ( 
            <div className="slidebar-container">
              <ToggleFriendFocus />
            </div>
          )}
          </div> 
      </div>
    </div>
  );
  
};

export default TabBarBanner;