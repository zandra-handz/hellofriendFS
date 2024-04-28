import React from 'react';
import { useNavigate } from 'react-router-dom';
import { FaSignOutAlt } from 'react-icons/fa';

function SignOutButton() {
    const navigate = useNavigate();

    const handleLogout = () => {
        // Display confirmation dialog
        if (window.confirm('Are you sure you want to sign out?')) {
            // If confirmed, navigate to the signout route
            navigate('/signout');
        }
    };

    return (
        <div className='header-item'>
            <button className="header-button" onClick={handleLogout} title="Sign out">
                <FaSignOutAlt />
            </button>
        </div>
    );
}

export default SignOutButton;
