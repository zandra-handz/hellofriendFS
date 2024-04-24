import React from 'react'; 
import '/src/styles/OldStyles.css';
import useThemeMode from '/src/hooks/UseThemeMode';

const Spinner = () => {
    const { themeMode } = useThemeMode();

  return (
    <div className={`${themeMode === 'dark' ? 'dark-mode' : ''}`}>
        <div className="spinner-container">
            <div className="spinner"></div>
        </div>
    </div>
  );
};

export default Spinner;



