import React, { useState } from 'react';
import api from '/src/api';
import useAuthUser from '/src/hooks/UseAuthUser';
import useFriendList from '/src/hooks/UseFriendList'; 
import '/src/styles/StylingFormsGeneral.css';

function FormLocationCreate({ onLocationCreate }) {
    const [title, setTitle] = useState('');
    const [address, setAddress] = useState('');
    const [personalExperience, setPersonalExperience] = useState(''); 
    const [selectedFriends, setSelectedFriends] = useState([]); 
    const [showSaveMessage, setShowSaveMessage] = useState(false); // State to manage save message visibility
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
            onLocationCreate(res.data); // Call the callback function to add the new location
            setShowSaveMessage(true); // Show the save message
            setTimeout(() => {
                setShowSaveMessage(false); // Hide the save message after 3 seconds
            }, 3000);
        } catch (error) {
            console.error('Error creating location:', error);
        }
    }

    return (
        <form onSubmit={handleSubmit} className='form-general-container'>
            <h1>Create Location</h1>
            {showSaveMessage && <p className="save-message">Location created successfully!</p>} {/* Render the save message */}
            <input
                className='form-general-input'
                type='text'
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder='Title'
            />
            <input
                className='form-general-input'
                type='text'
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                placeholder='Address'
            />
            <textarea
                className='form-general-input'
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
            <button className='form-general-button' type='submit'>
                Create Location
            </button>
        </form>
    );
}

export default FormLocationCreate;