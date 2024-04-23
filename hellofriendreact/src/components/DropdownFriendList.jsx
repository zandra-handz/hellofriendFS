import React from 'react';
import useFriendList from '../hooks/UseFriendList';
import '../styles/OldStyles.css'; // Import your CSS file for styling

const DropdownFriendList = () => {
  const { friendList } = useFriendList();

  // Render the dropdown options
  const renderOptions = () => {
    return friendList.map(friend => (
      <option key={friend.id} value={friend.id}>{friend.name}</option>
    ));
  };

  return (
    <select className="dropdown-menu"> {/* Apply your CSS class for styling */}
      <option value="">Select a friend</option>
      {renderOptions()}
    </select>
  );
};

export default DropdownFriendList;
