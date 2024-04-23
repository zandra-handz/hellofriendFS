import { useContext } from 'react';
import FocusModeContext from '../context/FocusModeProvider';

const useFocusMode = () => {
  const { focusMode, toggleFocusMode } = useContext(FocusModeContext);

  if (focusMode === undefined || toggleFocusMode === undefined) {
    throw new Error('useFocusMode must be used within a FocusModeProvider');
  }

  return { focusMode, toggleFocusMode };
};

export default useFocusMode;
