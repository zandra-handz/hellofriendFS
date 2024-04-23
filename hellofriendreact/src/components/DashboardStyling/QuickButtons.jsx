import React, { useState } from 'react';
import QuickThoughtCapsuleAddModal from './QuickThoughtCapsuleAddModal';
import AddHelloModal from './AddHelloModal';
import QuickImageAddModal from './QuickImageAddModal';
//import AddImageModal from './AddImageModal'; // Import the AddImageModal component
import '/src/styles/FriendSelectorStyler.css';
import useThemeMode from '/src/hooks/UseThemeMode';
import { FaGift, FaImage, FaHandHoldingHeart, FaCarSide } from 'react-icons/fa';

const QuickButtons = ({ buttonClassName }) => {
  const { themeMode } = useThemeMode();
  const [isIdeaModalOpen, setIsIdeaModalOpen] = useState(false);
  const [isHelloModalOpen, setIsHelloModalOpen] = useState(false);
  const [isImageModalOpen, setIsImageModalOpen] = useState(false);

  const openIdeaModal = () => {
    setIsIdeaModalOpen(true);
  };

  const openHelloModal = () => {
    setIsHelloModalOpen(true);
  };

  const openImageModal = () => {
    setIsImageModalOpen(true);
  };

  const closeAllModals = () => {
    setIsIdeaModalOpen(false);
    setIsHelloModalOpen(false);
    setIsImageModalOpen(false);
  };

  const handleSave = (text) => {
    console.log('Save Text:', text); 
  }; 

  return (
    <div className={`${themeMode === 'dark' ? 'dark-mode' : ''}`}>
      <div className="quick-buttons-container">
        <button className="capsule-button" onClick={openIdeaModal}>
          <FaHandHoldingHeart />
        </button>
        {isIdeaModalOpen && (
          <QuickThoughtCapsuleAddModal onClose={closeAllModals} onSave={handleSave} />
        )}
        <button className="image-button" onClick={openImageModal}>
          <FaImage />
        </button> 
        {isImageModalOpen && (
          <QuickImageAddModal onClose={closeAllModals} onSave={handleSave}/>
        )}

        <button className="hello-button" onClick={openHelloModal}>
          <FaCarSide />
        </button>
        {isHelloModalOpen && (
          <AddHelloModal onClose={closeAllModals} onSave={handleSave}/>
        )}


      </div>
    </div>
  );
};

export default QuickButtons;
