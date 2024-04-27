import React, { useMemo, useCallback } from 'react';
import Select from 'react-select';
import { FaHome } from 'react-icons/fa';
import useSelectedFriend from '../hooks/UseSelectedFriend';
import useFriendList from '../hooks/UseFriendList';
import useThemeMode from '../hooks/UseThemeMode';

const FriendSelector = () => {
    const { themeMode } = useThemeMode();
    const { selectedFriend, setFriend } = useSelectedFriend();
    const { friendList } = useFriendList([]);
    
    const handleSelectChange = useCallback((selectedOption) => {
        if (selectedOption && selectedOption.value === '') {
            setFriend(null);
        } else {
            const selectedFriendData = selectedOption ? selectedOption.data : null;
            setFriend(selectedFriendData);
        }
    }, [setFriend]);

    const options = useMemo(() => {
        if (!friendList) return [];
        return [
            { value: '', label: <FaHome /> }, 
            ...friendList.map((friend) => ({ value: friend.id, label: friend.name, data: friend })),
        ];
    }, [friendList]);

    // Define selectStyles inside the component body to recalculate when themeMode changes
    const selectStyles = useMemo(() => ({
        control: (provided, state) => ({
            ...provided,
            border: '1px solid transparent',
            borderRadius: '40px',
            backgroundColor: themeMode === 'dark' ? 'transparent' : 'white',
            width: 'auto',
            color: themeMode === 'dark' ? '#333' : 'transparent',
            borderColor: state.isFocused || state.isHovered ? 'transparent' : 'transparent', // Transparent border on hover or focus
            boxShadow: state.isFocused ? 'none' : provided.boxShadow,
            outline: 'none !important'
        }),
        singleValue: (provided, state) => ({
            ...provided,
            color: themeMode === 'dark' ? 'white' : 'black'
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
                        {/* Display additional details about the selected friend here */}
                    </div>
                )}
            </div>
        </div>
    );
};

export default React.memo(FriendSelector);
