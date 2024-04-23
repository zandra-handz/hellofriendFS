import React, { useState } from 'react';
import QuickImageAddModal from './QuickImageAddModal';
import '/src/styles/FriendSelectorStyler.css';
import useThemeMode from '/src/hooks/UseThemeMode';

const AddSShotsMemesButton = ({ buttonClassName }) => {
  const { themeMode } = useThemeMode();
  const [isModalOpen, setIsModalOpen] = useState(false);

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
          add image
        </button>
        {isModalOpen && (
          <QuickImageAddModal onClose={closeModal} onSave={handleSave} />
        )}
      </div>
    </div>
  );
};

export default AddSShotsMemesButton;