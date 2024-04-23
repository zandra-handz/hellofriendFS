import React, { useState } from 'react';
import api from '../api';
import useAuthUser from '../hooks/UseAuthUser';
import useFriendList from '../hooks/UseFriendList'; // Import the useFriendList hook
import '../styles/OldStyles.css';

function CreateLocationForm() {
    const [title, setTitle] = useState('');
    const [address, setAddress] = useState('');
    const [personalExperience, setPersonalExperience] = useState(''); 
    const [selectedFriends, setSelectedFriends] = useState([]); 
    const { authUser } = useAuthUser();
    const { friendList } = useFriendList(); // Fetch the list of friends

    const handleFriendSelect = (friendId) => {
        const index = selectedFriends.indexOf(friendId);
        if (index === -1) {
            setSelectedFriends([...selectedFriends, friendId]); // Add the selected friend ID to the list
        } else {
            const updatedFriends = [...selectedFriends];
            updatedFriends.splice(index, 1); // Remove the selected friend ID from the list
            setSelectedFriends(updatedFriends);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        try {
            const res = await api.post('/friends/locations/add/', {
                title: title,
                address: address,
                personal_experience_info: personalExperience, 
                user: authUser.user.id,
                friends: selectedFriends // Pass the IDs of selected friends
            });
        } catch (error) {
            console.error('Error creating location:', error);
        }
    }

    return (
        <form onSubmit={handleSubmit} className='form-container'>
            <h1>Create Location</h1>
            <input
                className='form-input'
                type='text'
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder='Title'
            />
            <input
                className='form-input'
                type='text'
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                placeholder='Address'
            />
            <textarea
                className='form-input'
                value={personalExperience}
                onChange={(e) => setPersonalExperience(e.target.value)}
                placeholder='Personal Experience Info'
            />
            <div className="friend-checkboxes-container">
                {friendList.map((friend, index) => (
                    <label key={index}>
                        <input
                            type="checkbox"
                            value={friend.id}
                            checked={selectedFriends.includes(friend.id)}
                            onChange={() => handleFriendSelect(friend.id)}
                        />
                        {friend.name}
                    </label>
                ))}
            </div>
            <button className='form-button' type='submit'>
                Create Location
            </button>
        </form>
    );
}

export default CreateLocationForm;
