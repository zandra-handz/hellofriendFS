import React, { useState, useEffect, useRef } from 'react';
import api from '/src/api';
import useAuthUser from '/src/hooks/UseAuthUser';
import useSelectedFriend from '/src/hooks/UseSelectedFriend';
import useThemeMode from '/src/hooks/UseThemeMode';
import '/src/styles/OldStyles.css';


const QuickImageAddModal = ({ onClose, onSave }) => {
  const { themeMode } = useThemeMode();
  const [image, setImage] = useState(null);
  const [imageCategory, setImageCategory] = useState('');
  const [title, setTitle] = useState('');
  const { authUser } = useAuthUser();
  const { selectedFriend } = useSelectedFriend();

  const handleImageChange = (e) => {
    setImage(e.target.files[0]);
  };

  const handleCategoryChange = (e) => {
    setImageCategory(e.target.value);
  };

  const handleTitleChange = (e) => {
    setTitle(e.target.value);
  };

  const handleSave = async () => {
    try {
      if (selectedFriend && image) {
        const formData = new FormData();
        formData.append('user', authUser.user.id);
        formData.append('friend', selectedFriend.id);
        formData.append('image', image);
        formData.append('image_category', imageCategory);
        formData.append('title', title);

        const response = await api.post(`/friends/${selectedFriend.id}/images/add/`, formData);

        setImage(null);
        setImageCategory('');
        setTitle('');
        onSave(); // Trigger the onSave callback to update the image list
      }
    } catch (error) {
      console.error('Error adding image:', error);
    }
  };

  return (
    <div className={`${themeMode === 'dark' ? 'dark-mode' : ''}`}>
      <div className="modal-overlay" style={{ zIndex: 9999 }}>
        <div className="modal-wrapper">
          <div className="modal-content">
            <span className="close-button" onClick={onClose}>
              &times;
            </span>
            <div className="modal-title-container">
              <div>
                <h1>Add an Image</h1>
              </div>
            </div>
            <div className="modal-content-container">
              <div className="modal-input-container">
                <div className="input-container">
                  <input type="file" onChange={handleImageChange} />
                </div>
                <div className="input-container">
                  <label htmlFor="imageCategory">Image Category</label>
                  <input type="text" id="imageCategory" value={imageCategory} onChange={handleCategoryChange} />
                </div>
                <div className="input-container">
                  <label htmlFor="title">Title</label>
                  <input type="text" id="title" value={title} onChange={handleTitleChange} />
                </div>
              </div>
            </div>
            <div className="modal-save-button-container">
              <button className="modal-save-button" onClick={handleSave} disabled={!image}>
                Save
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default QuickImageAddModal;
