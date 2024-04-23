import React from 'react';
import ToggleTheme from './ToggleTheme'; // Assuming ToggleTheme is your toggle button component
import '/src/styles/OldStyles.css'; // Assuming you have your styles imported here
import useAuthUser from '/src/hooks/UseAuthUser'; 
import useSelectedFriend from '/src/hooks/UseSelectedFriend'; 
import useThemeMode from '/src/hooks/UseThemeMode';
import SignOutButton from './SignOutButton';
import ThemeSunMoonButton from './ThemeSunMoonButton';
import { FaBars, FaPalette, FaSun, FaYinYang, FaUser, FaMoon } from 'react-icons/fa';

const Header = () => {
  const { themeMode } = useThemeMode();
  const { authUser } = useAuthUser();
  const { selectedFriend } = useSelectedFriend(); 
  

  function toggleDarkMode() {
    var element = document.body;
    element.classList.toggle("dark-mode");
  }

  return (
    <div className={`${themeMode === 'dark' ? 'dark-mode' : ''}`}>
      <div className="header">
        <div className='header-item'> 
          <p>{authUser.user && authUser.user.username} </p>
        </div>
        <div className='header-item'> 
          <ThemeSunMoonButton /> 
        </div>
        <div className='header-item'> 
          <SignOutButton />
        </div>
      </div>
    </div>
  );
};

export default Header;
