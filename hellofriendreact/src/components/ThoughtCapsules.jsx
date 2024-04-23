import React, { useState, useEffect } from 'react';
import api from '../api';

function ThoughtCapsules({ selectedFriend }) {
    
    const [thoughtCapsules, setThoughtCapsules] = useState([]);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const response = await api.get(`/friends/${selectedFriend}/thoughtcapsules/`);
                setThoughtCapsules(response.data);
            } catch (error) {
                console.error('Error fetching thought capsules:', error);
            }
        };
        if (selectedFriend) {
            fetchData();
        }
    }, [selectedFriend]);

    const handleDelete = async (thoughtCapsuleId) => {
        try {
            await api.delete(`/friends/thoughtcapsules/${thoughtCapsuleId}/`);
            setThoughtCapsules(thoughtCapsules.filter(tc => tc.id !== thoughtCapsuleId));
        } catch (error) {
            console.error('Error deleting thought capsule:', error);
        }
    };

    return (
        <div>
            <h2>Thought Capsules</h2>
            <ul>
                {thoughtCapsules.map(thoughtCapsule => (
                    <li key={thoughtCapsule.id}>
                        <p>{thoughtCapsule.content}</p>
                        <button onClick={() => handleDelete(thoughtCapsule.id)}>Delete</button>
                    </li>
                ))}
            </ul>
        </div>
    );
}

export default ThoughtCapsules;
