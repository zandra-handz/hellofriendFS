import { useContext } from 'react';
import SelectedFriendContext from '../context/SelectedFriendProvider';

const useSelectedFriend = () => {
  const context = useContext(SelectedFriendContext);

  if (!context) {
    throw new Error('useSelectedFriend must be used within a SelectedFriendProvider');
  }

  return context;
};

export default useSelectedFriend;