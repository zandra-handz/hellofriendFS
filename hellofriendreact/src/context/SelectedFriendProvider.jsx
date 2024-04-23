// SelectedFriendProvider.jsx
import React, { createContext, useContext, useState, useEffect } from 'react';

const SelectedFriendContext = createContext({});

export const SelectedFriendProvider = ({ children }) => {
  // Retrieve selected friend from local storage or default to null
  // const storedFriend = JSON.parse(localStorage.getItem('selectedFriend')) || null;

  // Uncomment the line above if you want to use localStorage
  const storedFriend = null;  // Comment this line out if you use localStorage

  const [selectedFriend, setFriend] = useState(storedFriend);

  // Save selected friend to local storage whenever it changes
  // useEffect(() => {
  //   localStorage.setItem('selectedFriend', JSON.stringify(selectedFriend));
  // }, [selectedFriend]);

  console.log('Selected Friend Provider', selectedFriend);

  return (
    <SelectedFriendContext.Provider value={{ selectedFriend, setFriend }}>
      {children}
    </SelectedFriendContext.Provider>
  );
};

export default SelectedFriendContext;