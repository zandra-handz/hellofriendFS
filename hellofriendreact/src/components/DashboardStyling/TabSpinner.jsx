import React from 'react'; 
import '/src/styles/OldStyles.css';
import useThemeMode from '/src/hooks/UseThemeMode';

const TabSpinner = () => {
    const { themeMode } = useThemeMode();

  return (
    <div className={`${themeMode === 'dark' ? 'dark-mode' : ''}`}>
        <div className="tab-spinner-container">
            <div className="tab-spinner"></div>
        </div>
    </div>
  );
};

export default TabSpinner; 
 
 
