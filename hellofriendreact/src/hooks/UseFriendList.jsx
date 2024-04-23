import { useContext } from 'react';
import FriendListContext from '../context/FriendListProvider';

const useFriendList = () => {
    const context = useContext(FriendListContext);

    if (!context) {
        throw new Error('useSelectedFriend must be used within a SelectedFriendProvider');
    }

    return context;
};

export default useFriendList;
