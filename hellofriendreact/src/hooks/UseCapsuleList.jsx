import { useContext } from 'react';
import CapsuleListContext from '../context/CapsuleListProvider'; // Adjust the import path as needed

const useCapsuleList = () => {
  const context = useContext(CapsuleListContext);

  if (!context) {
    throw new Error('useCapsuleList must be used within a CapsuleListProvider');
  }

  return context;
};

export default useCapsuleList;
