import React, { createContext, useContext, useState } from 'react';

const FocusModeContext = createContext({});

export const FocusModeProvider = ({ children }) => {
  const [focusMode, setFocusMode] = useState(false);

  const toggleFocusMode = () => {
    setFocusMode(prevMode => !prevMode);
  };

  return (
    <FocusModeContext.Provider value={{ focusMode, toggleFocusMode }}>
      {children}
    </FocusModeContext.Provider>
  );
};

export const useFocusMode = () => useContext(FocusModeContext);

export default FocusModeContext;
