import React from 'react';
import '/src/styles/OldStyles.css';
import useThemeMode from '/src/hooks/UseThemeMode';

const CardPlacesWide = ({ title, children }) => {
  const { themeMode } = useThemeMode();

  return (
    <div className={`${themeMode === 'dark' ? 'dark-mode' : ''}`}>
      <div className="places-card-wide">
        <div className="places-card-title">{title}</div>
        <div className="places-card-content">{children}</div>
      </div>
    </div>
  );
};

export default CardPlacesWide;