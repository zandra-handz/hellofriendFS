import React, { useState, useEffect, useRef } from 'react';
import { FaWrench, FaCaretDown, FaCaretRight } from 'react-icons/fa';
import '/src/styles/OldStyles.css';
import Spinner from './Spinner';
import useThemeMode from '/src/hooks/UseThemeMode';

const CardExpandAndConfig = ({ title, children, expanded, onEditButtonClick }) => {
  const [loading, setLoading] = useState(true); // State for loading spinner
  const { themeMode } = useThemeMode();
  const contentRef = useRef(null); // Ref for the content element

  useEffect(() => {
    // Simulate loading data
    setTimeout(() => {
      setLoading(false); // Set loading to false when data is ready
    }, 1000); // Simulated delay of 1 second
  }, []);

  const handleHeaderClick = () => {
    if (onEditButtonClick) {
      onEditButtonClick();
    }
  };

  return (
    <div className={`${themeMode === 'dark' ? 'dark-mode' : ''}`}>
      <div className="edit-card">
        <div className="edit-card-header" onClick={handleHeaderClick}>
          <h5>{title}</h5>
          <button className="edit-button">
            {expanded ? <FaCaretDown /> : <FaCaretRight />}
          </button>
        </div>
        {loading ? ( // Conditionally render loading spinner if data isn't ready yet
          <Spinner />
        ) : (
          <div
            className="edit-card-content"
            style={{ display: expanded ? 'block' : 'none' }}
            ref={contentRef} // Assign ref to the content element
            tabIndex={-1} // Make content focusable
          >
            {children}
          </div>
        )}
      </div>
    </div>
  );
};

export default CardExpandAndConfig;
