import React, { useState } from 'react';
import AddHelloModal from './AddHelloModal';
import '/src/styles/FriendSelectorStyler.css';
import useThemeMode from '/src/hooks/UseThemeMode';
import { FaSignOutAlt } from 'react-icons/fa';

const AddHelloButton = ({ buttonClassName }) => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const { themeMode } = useThemeMode();

  const openModal = () => {
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
  };

  const handleSave = (text) => {
    console.log('Text:', text);
    // Add any additional logic for handling the saved data
  };

  return (
    <div className={`${themeMode === 'dark' ? 'dark-mode' : ''}`}>
      <div className="friend-selector-container">
        <button className={buttonClassName} onClick={openModal}>
          add hello
        </button>
        {isModalOpen && (
          <AddHelloModal onClose={closeModal} onSave={handleSave} />
        )}
      </div>
    </div>
  );
};

export default AddHelloButton;