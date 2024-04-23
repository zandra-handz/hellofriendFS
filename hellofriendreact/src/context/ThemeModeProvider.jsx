import React, { createContext, useContext, useState } from 'react';

const ThemeModeContext = createContext({});

export const ThemeModeProvider = ({ children }) => {
  const [themeMode, setThemeMode] = useState('light');

  const toggleThemeMode = () => {
    setThemeMode(prevMode => (prevMode === 'light' ? 'dark' : 'light'));
  };

  return (
    <ThemeModeContext.Provider value={{ themeMode, toggleThemeMode }}>
      {children}
    </ThemeModeContext.Provider>
  );
};

export default ThemeModeContext;
