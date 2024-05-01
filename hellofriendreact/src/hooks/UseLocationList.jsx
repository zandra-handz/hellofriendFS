// useLocationList.js
import { useContext } from 'react';
import LocationListContext from '../context/LocationListProvider'; // Update the path accordingly

const useLocationList = () => {
  const context = useContext(LocationListContext);

  if (!context) {
    throw new Error('useLocationList must be used within a LocationListProvider');
  }

  return context;
};

export default useLocationList;
