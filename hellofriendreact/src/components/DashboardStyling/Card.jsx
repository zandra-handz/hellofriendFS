import React from 'react';
import '/src/styles/OldStyles.css'; 
import useThemeMode from '/src/hooks/UseThemeMode';

const Card = ({ title, children }) => {
  const { themeMode } = useThemeMode();

  return (
    <div className={`${themeMode === 'dark' ? 'dark-mode' : ''}`}>
      <div className="card"> 
        <div className="card-title">{title}</div>
        <div className="card-content">{children}</div>
      </div>
    </div>
  );
};

export default Card;
