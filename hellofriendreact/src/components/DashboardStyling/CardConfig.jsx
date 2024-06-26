import React from 'react';
import { FaWrench } from 'react-icons/fa';
import '/src/styles/OldStyles.css';
import useThemeMode from '/src/hooks/UseThemeMode';

const CardConfig = ({ title, children, onEditButtonClick }) => { 
  const { themeMode } = useThemeMode();

  return (
    <div className={`${themeMode === 'dark' ? 'dark-mode' : ''}`}>
      <div className="edit-card">
        <div className="edit-card-header">
          <h5>{title}</h5>
          <button className="edit-button" onClick={onEditButtonClick}> {/* Call onEditButtonClick */}
            <FaWrench />
          </button>
        </div>
        <div className="edit-card-content">{children}</div>
      </div>
    </div>
  );
};

export default CardConfig;
