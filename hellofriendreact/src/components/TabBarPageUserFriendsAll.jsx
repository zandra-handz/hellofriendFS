import React, { useState, useEffect } from 'react';
import CardExpand from './DashboardStyling/CardExpand';
import useFriendList from '../hooks/UseFriendList';
import CreateFriend from './CreateFriend';
import useAuthUser from '../hooks/UseAuthUser';
import api from '../api';

const TabBarPageUserFriendsAll = () => {
    const { friendList, setFriendList } = useFriendList();
    const { authUser } = useAuthUser();
    const [openFriendDetails, setOpenFriendDetails] = useState(null);
    const [friendDetails, setFriendDetails] = useState(null);
    const [showDeleteConfirmation, setShowDeleteConfirmation] = useState(false);
    const [editFavoritesMode, setEditFavoritesMode] = useState(false);
    const [selectedFavoriteLocations, setSelectedFavoriteLocations] = useState([]);
    const [availableLocations, setAvailableLocations] = useState([]);

    useEffect(() => {
        const fetchFriendDetails = async (friendId) => {
            try {
                const response = await api.get(`/friends/${friendId}/`);
                setFriendDetails(response.data);
            } catch (error) {
                console.error('Error fetching friend details:', error);
            }
        };

        if (openFriendDetails !== null) {
            fetchFriendDetails(openFriendDetails);
        }
    }, [openFriendDetails]);

    useEffect(() => {
        const fetchAvailableLocations = async () => {
            try {
                const response = await api.get('/friends/locations/all/');
                setAvailableLocations(response.data);
            } catch (error) {
                console.error('Error fetching available locations:', error);
            }
        };

        if (editFavoritesMode) {
            fetchAvailableLocations();
        }
    }, [editFavoritesMode]);

    const handleToggleDetails = (friendId) => {
        setOpenFriendDetails((prevFriendId) => (prevFriendId === friendId ? null : friendId));
    };

    const handleDeleteFriend = async () => {
        try {
            await api.delete(`/friends/${openFriendDetails}/`);
            setFriendList(friendList.filter((friend) => friend.id !== openFriendDetails));
            setOpenFriendDetails(null);
            setFriendDetails(null);
            setShowDeleteConfirmation(false);
        } catch (error) {
            console.error('Error deleting friend:', error);
        }
    };

    const handleCancelDelete = () => {
        setShowDeleteConfirmation(false);
    };

    const handleEditFriendInfo = () => {
        // Handle edit friend info action
    };

    const handleEditSettings = () => {
        // Handle edit settings action
    };

    const handleEditFavorites = () => {
        setEditFavoritesMode(true);
        setSelectedFavoriteLocations(friendDetails.friend_faves.locations);
    };

    const handleSaveFavorites = async () => {
        try {
            await api.put(`/friends/${openFriendDetails}/faves/`, {
                user: authUser.user.id,
                friend: openFriendDetails,
                locations: selectedFavoriteLocations
            });
            setEditFavoritesMode(false);
            // Refresh friend details after saving changes
            const response = await api.get(`/friends/${openFriendDetails}/`);
            setFriendDetails(response.data);
        } catch (error) {
            console.error('Error updating favorites:', error);
        }
    };

    const handleFavoriteCheckboxChange = (locationId) => {
        setSelectedFavoriteLocations((prevLocations) => {
            if (prevLocations.includes(locationId)) {
                return prevLocations.filter((id) => id !== locationId);
            } else {
                return [...prevLocations, locationId];
            }
        });
    };

    return (
        <div>
            <h1></h1>
            {friendList.map((friend, index) => (
                <CardExpand title={friend.name} expanded={openFriendDetails === friend.id} onExpandButtonClick={() => handleToggleDetails(friend.id)}>
                    {openFriendDetails === friend.id && friendDetails && (
                        <div className="friend-details">
                            <div>
                                <h3>Friend Info:</h3>
                                <p>Name: {friendDetails.name}</p>
                                <p>First Name: {friendDetails.first_name}</p>
                                <p>Last Name: {friendDetails.last_name}</p>
                                <p>First Meet Entered: {friendDetails.first_meet_entered}</p>
                                <button onClick={handleEditFriendInfo}>Edit</button>
                            </div>
                            <div>
                                <h3>Settings:</h3>
                                <p>Can Schedule: {friendDetails.suggestion_settings.can_schedule ? 'Yes' : 'No'}</p>
                                <p>Effort Required: {friendDetails.suggestion_settings.effort_required}</p>
                                <p>Priority Level: {friendDetails.suggestion_settings.priority_level}</p>
                                <p>Category Limit Formula: {friendDetails.suggestion_settings.category_limit_formula}</p>
                                <button onClick={handleEditSettings}>Edit</button>
                            </div>
                            <div>
                                <h3>Favorites:</h3>
                                <h1>Locations:</h1>
                                {editFavoritesMode ? (
                                    <div>
                                        {availableLocations.map((location) => (
                                            <label key={location.id}>
                                                <input
                                                    type="checkbox"
                                                    checked={selectedFavoriteLocations.includes(location.id)}
                                                    onChange={() => handleFavoriteCheckboxChange(location.id)}
                                                />
                                                {location.title}
                                            </label>
                                        ))}
                                        <button onClick={handleSaveFavorites}>Save</button>
                                    </div>
                                ) : (
                                    <p>
                                        {friendDetails.friend_faves.locations.map((location) => location.title).join(', ')}
                                    </p>
                                )}
                                <button onClick={handleEditFavorites}>Edit</button>
                            </div>
                            <button onClick={() => setShowDeleteConfirmation(true)}>Delete</button>
                        </div>
                    )}
                </CardExpand>
            ))}
            <CreateFriend />

            {showDeleteConfirmation && (
                <div className="delete-confirmation-modal">
                    <p>Are you sure you want to delete this friend?</p>
                    <button onClick={handleDeleteFriend}>Yes</button>
                    <button onClick={handleCancelDelete}>No</button>
                </div>
            )}
        </div>
    );
};

export default TabBarPageUserFriendsAll;
