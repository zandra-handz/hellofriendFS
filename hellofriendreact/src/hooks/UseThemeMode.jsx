import { useContext } from 'react';
import ThemeModeContext from '../context/ThemeModeProvider';

const useThemeMode = () => {
  const { themeMode, toggleThemeMode } = useContext(ThemeModeContext);

  if (!themeMode || !toggleThemeMode) {
    throw new Error('useThemeMode must be used within a ThemeModeProvider');
  }

  return { themeMode, toggleThemeMode };
};

export default useThemeMode;
