import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../api';

const FriendListContext = createContext({ friendList: [], setFriendList: () => {} });

export const FriendListProvider = ({ children }) => {
  const [friendList, setFriendList] = useState([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await api.get('/friends/all/');
        const friendData = response.data;
        // Extract and set the friend list
        const friendList = friendData.map(friend => ({ id: friend.id, name: friend.name }));
        setFriendList(friendList);
      } catch (error) {
        console.error('Error fetching friend list:', error);
      }
    };
    console.log('Friendlist data: ', friendList)
    fetchData();
  }, []);

  return (
    <FriendListContext.Provider value={{ friendList, setFriendList }}>
      {children}
    </FriendListContext.Provider>
  );
};

export const useFriendList = () => useContext(FriendListContext);

export default FriendListContext;
