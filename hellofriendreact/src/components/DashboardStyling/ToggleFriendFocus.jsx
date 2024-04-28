import React from 'react';
import useFocusMode from '/src/hooks/UseFocusMode';


const ToggleFriendFocus = () => {
  const { focusMode, toggleFocusMode } = useFocusMode();

  return (
    <div className={`${focusMode ? 'focus-mode' : ''}`}>
      <div className="slider-container" onClick={toggleFocusMode}>
        <div className={`slider ${focusMode ? 'slider-focus' : 'slider-blur'}`}></div>
        <div className="slider-text">{focusMode ? 'Focus' : ''}</div>
      </div>
    </div>
  );
};

export default ToggleFriendFocus;
