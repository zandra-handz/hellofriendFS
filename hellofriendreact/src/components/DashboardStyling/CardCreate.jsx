import React, { useState } from 'react';
import { FaPlus, FaMinus } from 'react-icons/fa';
import '/src/styles/OldStyles.css';
import useThemeMode from '/src/hooks/UseThemeMode';

const CardCreate = ({ title, children, onClick }) => {
  const [expanded, setExpanded] = useState(false);
  const { themeMode } = useThemeMode();

  const toggleExpand = () => {
    setExpanded(prevExpanded => !prevExpanded);
  };

  return (
    <div className={`${themeMode === 'dark' ? 'dark-mode' : ''}`}>
      <div className="edit-card">
        <div className="edit-card-header" onClick={() => { toggleExpand(); onClick(); }}>
          <h5>{title}</h5>
          <button className="edit-button">
            {expanded ? <FaMinus /> : <FaPlus />}
          </button>
        </div>
      
        {expanded && (
          <div className="edit-card-content">
            {children}
          </div>
        )}
      </div>
    </div>
  );
};

export default CardCreate;
