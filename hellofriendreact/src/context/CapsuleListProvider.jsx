import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../api';
import useSelectedFriend from '../hooks/UseSelectedFriend'; // Adjust the import path as needed

const CapsuleListContext = createContext({ capsuleList: [], setCapsuleList: () => {} });

export const CapsuleListProvider = ({ children }) => {
  const { selectedFriend } = useSelectedFriend(); // Access selected friend using your custom hook
  const [capsuleList, setCapsuleList] = useState([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        if (selectedFriend) {
          const response = await api.get(`/friends/${selectedFriend.id}/thoughtcapsules/`);
          const capsuleData = response.data;
          const formattedCapsuleList = capsuleData.map(capsule => ({
            id: capsule.id,
            typedCategory: capsule.typed_category,
            capsule: capsule.capsule
          }));
          setCapsuleList(formattedCapsuleList);
        }
      } catch (error) {
        console.error('Error fetching capsule list:', error);
      }
    };

    fetchData();
  }, [selectedFriend]);

  return (
    <CapsuleListContext.Provider value={{ capsuleList, setCapsuleList }}>
      {children}
    </CapsuleListContext.Provider>
  );
};

export const useCapsuleList = () => useContext(CapsuleListContext);


export default CapsuleListContext;