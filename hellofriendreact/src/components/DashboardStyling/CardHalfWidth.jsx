import React from 'react';
import '/src/styles/OldStyles.css'; 
import useThemeMode from '/src/hooks/UseThemeMode';

const CardHalfWidth = ({ title, children }) => {
  const { themeMode } = useThemeMode();

  return (
    <div className={`${themeMode === 'dark' ? 'dark-mode' : ''}`}>
      <div className="card-half-width"> 
        <div className="card-title">{title}</div>
        <div className="card-content">{children}</div>
      </div>
    </div>
  );
};

export default CardHalfWidth;
