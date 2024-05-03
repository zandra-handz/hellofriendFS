import { useContext } from 'react';
import SelectedFriendContext from '../context/SelectedFriendProvider';

const useSelectedFriend = () => {
  const context = useContext(SelectedFriendContext);

  if (!context) {
    throw new Error('useSelectedFriend must be used within a SelectedFriendProvider');
  }

  return {
    ...context,
    setFriendDashboardData: context.setFriendDashboardData, // Include setFriendDashboardData in the returned object
    friendDashboardData: context.friendDashboardData // Include dashboard data in the returned object
  };
};

export default useSelectedFriend;
