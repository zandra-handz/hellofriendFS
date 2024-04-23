import React from 'react';
import '/src/styles/OldStyles.css';
import useThemeMode from '/src/hooks/UseThemeMode';


const Tab = ({ label, active, onClick, children }) => {
  const { themeMode } = useThemeMode();

  return (
    <div className={`${themeMode === 'dark' ? 'dark-mode' : ''}`}>
      <div className={`tab-btn ${active ? 'active' : ''}`} onClick={onClick}>
        <div>{label}</div>
      </div>
    </div>
  );
};

export default Tab;