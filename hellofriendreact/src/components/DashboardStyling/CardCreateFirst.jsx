import React, { useState } from 'react';
import { FaPlus, FaMinus } from 'react-icons/fa';
import '/src/styles/OldStyles.css';
import useThemeMode from '/src/hooks/UseThemeMode';

const CardCreateFirst = ({ title, children }) => {
  const { themeMode } = useThemeMode();



  return (
    <div className={`${themeMode === 'dark' ? 'dark-mode' : ''}`}>
      <div className="edit-card">
        <div className="edit-card-header" >
          <h5>{title}</h5>
        </div>
       
          <div className="edit-card-content">
            {children}
          </div>
       
      </div>
    </div>
  );
};

export default CardCreateFirst;
