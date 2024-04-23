import React from 'react';
import { FaPenFancy } from 'react-icons/fa';
import '/src/styles/OldStyles.css';
import useThemeMode from '/src/hooks/UseThemeMode';

const CardUneditable = ({ title, children }) => {
  const { themeMode } = useThemeMode();

  return (
    <div className={`${themeMode === 'dark' ? 'dark-mode' : ''}`}>
      <div className="edit-card">
        <div className="edit-card-header">
          <h2>{title}</h2>
          <button className="edit-button" onClick={() => console.log('Edit clicked')}>
            
          </button>
        </div>
      
        <div className="edit-card-content">{children}</div>
      </div>
    </div>
  );
};

export default CardUneditable;