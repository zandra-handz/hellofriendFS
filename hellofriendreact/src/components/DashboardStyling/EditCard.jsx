import React from 'react';
import { FaPen } from 'react-icons/fa';
import '/src/styles/OldStyles.css';
import useThemeMode from '/src/hooks/UseThemeMode';

const EditCard = ({ title, children, onEditButtonClick }) => { 
  const { themeMode } = useThemeMode();

  return (
    <div className={`${themeMode === 'dark' ? 'dark-mode' : ''}`}>
      <div className="edit-card">
        <div className="edit-card-header">
          <h2>{title}</h2>
          <button className="edit-button" onClick={onEditButtonClick}> {/* Call onEditButtonClick */}
            <FaPen />
          </button>
        </div>
        <div className="edit-card-content">{children}</div>
      </div>
    </div>
  );
};

export default EditCard;
