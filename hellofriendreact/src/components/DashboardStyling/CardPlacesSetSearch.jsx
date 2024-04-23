import React from 'react';
import '/src/styles/OldStyles.css';
import useThemeMode from '/src/hooks/UseThemeMode';
import { FaArrowRight, FaArrowLeft } from 'react-icons/fa';

const CardPlacesSetSearch = ({ children, showRedoButton, onRedoButtonClick, isRedoMode }) => {
  const { themeMode } = useThemeMode();

  return (
    <div className={`${themeMode === 'dark' ? 'dark-mode' : ''}`}>
      <div className="places-card"> 
        <div className="places-card-header">
            <h2> </h2>
            <div>
              {showRedoButton && (  
                <button onClick={onRedoButtonClick} className="redo-button">
                  {isRedoMode ? <FaArrowRight /> : <FaArrowLeft />}
                </button>
              )}
            </div>
          </div>
        <div className="places-card-content">
          {children}
        </div>

      </div>
    </div>
  );
};

export default CardPlacesSetSearch;
