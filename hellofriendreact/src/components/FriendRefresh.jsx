import React, { useEffect } from 'react';
import useSelectedFriend from '../hooks/UseSelectedFriend';

const FriendRefresh = ({ friendId }) => {
    const { setFriend } = useSelectedFriend();

    useEffect(() => {
        // Set the selected friend using the provided friendId
        setFriend(friendId);
    }, [setFriend, friendId]);

    return null; // Since this component doesn't render anything, return null
};

export default FriendRefresh;
