import React from 'react';
import useFocusMode from '/src/hooks/UseFocusMode';

const ToggleFriendFocus = () => {
  const { focusMode, toggleFocusMode } = useFocusMode();

  const sliderStyle = {
    backgroundColor: focusMode ? '#04D9FF': '#a2a3a0',
    transform: !focusMode ? 'translateX(100%)' : 'translateX(0)',
  };

  return (
    <div className={`${focusMode ? 'focus-mode' : ''}`}>
      <div className="slider-container" onClick={toggleFocusMode}>
        <div className="slider" style={sliderStyle}></div>
        <div className="slider-text">{focusMode ? 'Focus' : ''}</div>
      </div>
    </div>
  );
};

export default ToggleFriendFocus;
