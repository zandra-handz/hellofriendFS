// SelectedFriendProvider.jsx
import React, { createContext, useContext, useState, useEffect } from 'react';

const CapsuleContext = createContext({});

export const CapsuleProvider = ({ children }) => {
  // Retrieve selected friend from local storage or default to null
  // const storedFriend = JSON.parse(localStorage.getItem('selectedFriend')) || null;

  // Uncomment the line above if you want to use localStorage
  const storedCapsules = null;  // Comment this line out if you use localStorage

  const [capsules, setCapsules] = useState(storedCapsules);

  // Save selected friend to local storage whenever it changes
  // useEffect(() => {
  //   localStorage.setItem('selectedFriend', JSON.stringify(selectedFriend));
  // }, [selectedFriend]);

  console.log('Capsule Provider', capsules);

  return (
    <CapsuleContext.Provider value={{ capsules, setCapsules }}>
      {children}
    </CapsuleContext.Provider>
  );
};

export default CapsuleContext;