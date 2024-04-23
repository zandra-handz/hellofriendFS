import React, { useEffect, useState, useMemo, useCallback } from 'react';
import api from '../api';
import Select from 'react-select';
import { FaHome } from 'react-icons/fa';
import useSelectedFriend from '../hooks/UseSelectedFriend';
import useFriendList from '../hooks/UseFriendList';
import useThemeMode from '../hooks/UseThemeMode';

const FriendSelector = () => {
    const { themeMode } = useThemeMode();
    const { selectedFriend, setFriend } = useSelectedFriend();
    const { friendList, setFriendList } = useFriendList([]);
    const [initialData, setInitialData] = useState(null);
    const [refreshIndicator, setRefreshIndicator] = useState(false); // State to trigger refresh

    useEffect(() => {
        const fetchData = async () => {
            try {
                const response = await api.get('/friends/all/');
                const friendData = response.data;
                setInitialData(friendData);
                setFriendList(friendData.map((friend) => ({ id: friend.id, name: friend.name })));
            } catch (error) {
                console.error('Error fetching data:', error);
            }
        };

        fetchData();
    }, [setFriendList, refreshIndicator]); // Include refreshIndicator in dependencies

    useEffect(() => {
        // Logic to handle the effect when the length of the friendList changes
        console.log('Length of friendList changed. Refreshing FriendSelector...');
        // Set refreshIndicator to trigger a re-fetch
        setRefreshIndicator(prevState => !prevState);
    }, [friendList.length]); // Include friendList length in dependencies

    const handleSelectChange = useCallback((selectedOption) => {
        if (selectedOption && selectedOption.value === '') {
            setFriend(null);
        } else {
            const selectedFriendData = selectedOption ? selectedOption.data : null;
            setFriend(selectedFriendData);
        }
    }, [setFriend]);

    const options = useMemo(() => {
        if (!initialData) return [];
        return [
            { value: '', label: <FaHome /> }, 
            ...initialData.map((item) => ({ value: item.id, label: item.name, data: item })),
        ];
    }, [initialData]);

    console.log('Selected Friend in FriendSelector:', selectedFriend);

    // Define selectStyles inside the component body to recalculate when themeMode changes
    const selectStyles = useMemo(() => ({
        control: (provided, state) => ({
            ...provided,
            border: '1px solid transparent',
            borderRadius: '18px',
            backgroundColor: themeMode === 'dark' ? 'transparent' : 'transparent',
            color: themeMode === 'dark' ? '#333' : 'transparent',
            borderColor: state.isFocused || state.isHovered ? 'transparent' : 'transparent', // Transparent border on hover or focus
            boxShadow: state.isFocused ? 'none' : provided.boxShadow,
            outline: 'none !important'
        }),
        singleValue: (provided, state) => ({
            ...provided,
            color: themeMode === 'dark' ? 'white' : 'black',
            fontSize: '20px' ,
            fontWeight: '500'
        }),
        indicatorSeparator: () => ({ display: 'none' }), // Hide the indicator separator
        indicator: (provided, state) => ({
            ...provided,
            color: 'transparent', // Make the indicator transparent
            '&:hover': {
                color: 'transparent' // Make the indicator transparent on hover
            }
        }),
        menu: (provided, state) => ({
            ...provided,
            borderRadius: '18px',
            backgroundColor: themeMode === 'dark' ? '#555' : '#fff',
            width: '300px',
            display: 'flex',
            flexDirection: 'column',
            maxHeight: '200px',
            overflowY: 'auto',
        }),
        option: (provided, state) => ({
            ...provided,
            color: state.isSelected ? 'white' : 'black',
            backgroundColor: state.isSelected ? 'gray' : 'transparent',
            '&:hover': {
                
                backgroundColor: 'gray',
                color: 'white',
            },
        }),
    }), [themeMode]);

    return (
        <div className={`${themeMode === 'dark' ? 'dark-mode' : ''}`}>
            <div className="friend-selector-container">
                <Select
                    options={options}
                    value={selectedFriend ? { value: selectedFriend.id, label: selectedFriend.name } : null}
                    onChange={handleSelectChange}
                    placeholder={<FaHome />}
                    className="react-select-container"
                    styles={selectStyles} // Pass the styles object to the styles prop
                    menuPortalTarget={document.body}
                    isSearchable={false}
                />

                {selectedFriend && (
                    <div>
                        <h2></h2>
                        {/* Display additional details about the selected friend here */}
                    </div>
                )}
            </div>
        </div>
    );
};

export default FriendSelector;
