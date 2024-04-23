import React from 'react';
import { useNavigate } from 'react-router-dom';
import { FaSignOutAlt } from 'react-icons/fa';
import '/src/styles/OldStyles.css';

function SignOutButton() {
  const navigate = useNavigate();

  const handleLogout = () => { 
    navigate('/signout');
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
