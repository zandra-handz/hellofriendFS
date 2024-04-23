import React from 'react';
import useThemeMode from '../hooks/UseThemeMode';

function Friend({ friends, selectedFriendId, onDelete }) {
    const { themeMode } = useThemeMode();

    if (!selectedFriendId) {
        return <p></p>;
    }

    const selectedFriend = friends.find((friend) => friend.id === selectedFriendId);

    if (!selectedFriend) {
        return <p>Friend not found</p>;
    }

    const formattedDate = new Date(selectedFriend.created_on).toLocaleDateString('en-US');
    
    // I don't know if this works
    const formattedNextDate = new Date(selectedFriend.nextMeet).toLocaleDateString('en-US');

    return (
        <div className={`${themeMode === 'dark' ? 'dark-mode' : ''}`}>
            <div className='note-container'>
                <p className='note-title'>{selectedFriend.name}</p>
                <p className='note-content'>{selectedFriend.effort_required}</p>
                <p className='note-title'>{selectedFriend.priority_level}</p>
                <p className='note-date'>{formattedDate}</p>
                <p className='friend-next-date'>{formattedNextDate}</p>
                <button className='delete-button' onClick={() => onDelete(selectedFriend.id)}>
                    Delete
                </button>
            </div>
        </div>
    );
}

export default Friend;
