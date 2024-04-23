import React from 'react';
import useThemeMode from '/src/hooks/UseThemeMode';

const ToggleTheme = () => {
  const { themeMode, toggleThemeMode } = useThemeMode();

  const sliderStyle = {
    backgroundColor: themeMode === 'light' ? '#f1c40f' : '#34495e',
    transform: themeMode === 'light' ? 'translateX(0)' : 'translateX(100%)',
  };

  return (
    <div className={`${themeMode === 'dark' ? 'dark-mode' : ''}`}>
      <div className="slider-container" onClick={toggleThemeMode}>
        <div className="slider" style={sliderStyle}></div>
        <div className="slider-text">{themeMode === 'light' ? 'Light' : 'Dark'}</div>
      </div>
    </div>
  );
};

export default ToggleTheme;

