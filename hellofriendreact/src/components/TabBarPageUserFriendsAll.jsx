import React, { useState } from 'react';
import CardExpand from './DashboardStyling/CardExpand';
import ButtonRemixAll from './DashboardStyling/ButtonRemixAll';
import useFriendList from '../hooks/UseFriendList';
import CreateFriend from './CreateFriend';
import api from '../api';
import useUpcomingHelloes from '../hooks/UseUpcomingHelloes';

const TabBarPageUserFriendsAll = () => {
    const { friendList, setFriendList } = useFriendList();
    const [selectedFriendId, setSelectedFriendId] = useState(null);
    const { setUpdateTrigger } = useUpcomingHelloes();
    const [openFriendDetails, setOpenFriendDetails] = useState(null);

    const handleRemixComplete = () => { 
        setUpdateTrigger(prev => !prev);
    };

    const handleDeleteFriend = async (friendId) => {
        try {
            await api.delete(`/friends/${friendId}/`);
            setFriendList(friendList.filter((friend) => friend.id !== friendId));
            setSelectedFriendId(null);
            setUpdateTrigger(prev => !prev);
        } catch (error) {
            console.error('Error deleting friend:', error);
        }
    };

    const handleToggleDetails = (friendId) => {
        setOpenFriendDetails(openFriendDetails === friendId ? null : friendId);
    };

    const handleToggleDeleteConfirmation = (friendId) => {
        const confirmed = window.confirm('Are you sure you want to delete this friend?');
        if (confirmed) {
            handleDeleteFriend(friendId);
        }
    };

    return (
        <div>
            <h1></h1>
            <div>
                <ButtonRemixAll onRemix={handleRemixComplete} />
            </div>
            {friendList.map((friend, index) => (
                <CardExpand 
                    key={friend.id} 
                    title={friend.name} 
                    expanded={openFriendDetails === friend.id} 
                    onExpandButtonClick={() => handleToggleDetails(friend.id)}
                >
                    {openFriendDetails === friend.id && (
                        <div>
                            <button onClick={() => handleToggleDeleteConfirmation(friend.id)}>Delete</button>
                        </div>
                    )}
                </CardExpand>
            ))}

            <CreateFriend />
        </div>
    );
};

export default TabBarPageUserFriendsAll;
