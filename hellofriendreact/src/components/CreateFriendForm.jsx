import React, { useState } from 'react';
import api from '../api';
import useThemeMode from '../hooks/UseThemeMode';
import useFriendList from '../hooks/UseFriendList'; // Import hook to access friendList state

function CreateFriendForm() {
    const { themeMode } = useThemeMode();
    const [friendName, setFriendName] = useState('');
    const [firstName, setFirstName] = useState('');
    const [lastName, setLastName] = useState('');
    const [lastDate, setLastDate] = useState('');
    const [successMessage, setSuccessMessage] = useState(null); // State for success message
    const { friendList, setFriendList } = useFriendList([]); // Access friendList state

    const createFriend = async (e) => {
        e.preventDefault();
        const formattedDate = new Date(lastDate).toISOString().split('T')[0]; // Extract date part without time

        const postData = {
            name: friendName,
            first_name: firstName,
            last_name: lastName,
            first_meet_entered: formattedDate
        };

        try {
            const res = await api.post('/friends/create/', postData);
            if (res.status === 201) {
                const { id, name } = res.data; // Extract ID and name from response data
                setFriendList([...friendList, { id, name }]); // Add new friend to the friend list
                setSuccessMessage('Friend created!'); // Set success message
                // Reset form fields
                setFriendName('');
                setFirstName('');
                setLastName('');
                setLastDate('');
                // Clear success message after 3 seconds
                setTimeout(() => {
                    setSuccessMessage(null);
                }, 3000);
            } else {
                alert('Failed to make friend.');
            }
        } catch (error) {
            alert(error.message);
        }
    };

    return (
        <div className={`${themeMode === 'dark' ? 'dark-mode' : ''}`}>
            <div>
                <h2>Add a Friend</h2>
                <form onSubmit={createFriend}>
                    <label htmlFor="name">Name:</label><br />
                    <input
                        type="text"
                        id="name"
                        name="name"
                        required
                        value={friendName}
                        onChange={(e) => setFriendName(e.target.value)}
                    /><br />
                    <label htmlFor="first-name">First name:</label><br />
                    <input
                        id="first-name"
                        name="first_name"
                        required
                        value={firstName}
                        onChange={(e) => setFirstName(e.target.value)}
                    /><br />
                    <label htmlFor="last-name">Last name:</label><br />
                    <input
                        id="last-name"
                        name="last_name"
                        required
                        value={lastName}
                        onChange={(e) => setLastName(e.target.value)}
                    /><br />
                    <label htmlFor="first-meet-entered">Last meet up:</label><br />
                    <input
                        id="last-date"
                        name="first-meet-entered"
                        type="date"
                        required
                        value={lastDate}
                        onChange={(e) => setLastDate(e.target.value)}
                    /><br />
                    <input type="submit" value="Submit" />
                </form>
                {successMessage && (
                    <div className="success-message">{successMessage}</div>
                )}
            </div>
        </div>
    );
}

export default CreateFriendForm;
