// AddThoughtCapsule.js
import React, { useState } from 'react';
import api from '../api';
import useThemeMode from '../hooks/UseThemeMode';

function AddThoughtCapsule({ friendId, getThoughtCapsules }) {
    const { themeMode } = useThemeMode();
    const [typedCategory, setTypedCategory] = useState('');
    const [capsule, setCapsule] = useState('');

    const createThoughtCapsule = (e) => {
        e.preventDefault();

        const postData = {
            friend: friendId,
            typed_category: typedCategory,
            capsule: capsule,
        };

        api.post(`/friends/${friendId}/thoughtcapsules/add/`, postData) // Use the new endpoint to create thought capsules
            .then((res) => {
                if (res.status === 201) {
                    alert('Thought capsule added!');
                    getThoughtCapsules();
                } else {
                    alert('Failed to add thought capsule.');
                }
            })
            .catch((err) => alert(err));
    };

    return (
        <div className={`${themeMode === 'dark' ? 'dark-mode' : ''}`}>
            <div>
                <h2>Add a Thought Capsule</h2>
                <form onSubmit={createThoughtCapsule}>
                    <label htmlFor="typed-category">Typed Category:</label><br />
                    <input
                        type="text"
                        id="typed-category"
                        name="typed_category"
                        value={typedCategory}
                        onChange={(e) => setTypedCategory(e.target.value)}
                    /><br />
                    <label htmlFor="capsule">Capsule:</label><br />
                    <textarea
                        id="capsule"
                        name="capsule"
                        rows="4"
                        cols="50"
                        value={capsule}
                        onChange={(e) => setCapsule(e.target.value)}
                    ></textarea><br />
                    <input type="submit" value="Submit" />
                </form>
            </div>
        </div>
    );
}

export default AddThoughtCapsule;
