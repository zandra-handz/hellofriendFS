import React from 'react';
import { FaArrowDown, FaArrowRight } from 'react-icons/fa';
import '/src/styles/OldStyles.css';
import useThemeMode from '/src/hooks/UseThemeMode';

const CardExpand = ({ title, children, expanded, onExpandButtonClick }) => { 
  const { themeMode } = useThemeMode();

  return (
    <div className={`${themeMode === 'dark' ? 'dark-mode' : ''}`}>
      <div className="edit-card">
        <div className="edit-card-header" onClick={onExpandButtonClick}>
          <h5>{title}</h5>
          <button className="edit-button">
            {expanded ? <FaArrowDown /> : <FaArrowRight />}
          </button>
        </div>
        <div className="edit-card-content">{children}</div>
      </div>
    </div>
  );
};

export default CardExpand;
