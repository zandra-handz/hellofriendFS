import React, { useState, useEffect } from 'react';
import api from '/src/api';
import useAuthUser from '/src/hooks/UseAuthUser';
import useSelectedFriend from '/src/hooks/UseSelectedFriend';
import '/src/styles/OldStyles.css';
import useThemeMode from '/src/hooks/UseThemeMode';

const DetailImageModal = ({ imageId, onClose }) => {
  const { themeMode } = useThemeMode();
  const [image, setImage] = useState(null);
  const [isOpen, setIsOpen] = useState(false); // State to manage modal visibility
  const [deleteMessage, setDeleteMessage] = useState('');
  const { authUser } = useAuthUser();
  const { selectedFriend } = useSelectedFriend();

  useEffect(() => {
    const fetchImage = async () => {
      try {
        const response = await api.get(`/friends/${selectedFriend.id}/image/${imageId}/`);
        setImage(response.data);
        setIsOpen(true); // Open the modal after fetching the image
      } catch (error) {
        console.error('Error fetching image:', error);
        // Handle the error, e.g., by displaying a message to the user
        // You can set image to null to prevent the modal from rendering
        setImage(null);
      }
    };
  
    // Only fetch image if the imageId changes
    if (imageId !== null && imageId !== undefined) {
      fetchImage();
    }
  
  }, [imageId]); // Only re-run the effect when imageId changes
  

  const handleClose = () => {
    setIsOpen(false);
    onClose();
  };

  const handleDelete = async () => {
    try {
      await api.delete(`/friends/${selectedFriend.id}/image/${imageId}/`);
      setDeleteMessage('Image deleted!');
      setTimeout(() => {
        setDeleteMessage('');
        setIsOpen(false); // Close the modal
        onClose(); // Call onClose to handle any additional actions
      }, 2000); // Close modal after 2 seconds
    } catch (error) {
      console.error('Error deleting image:', error);
    }
  };

  return (
    isOpen && image && (
      <div className={`${themeMode === 'dark' ? 'dark-mode' : ''}`}>
        <div className="modal-overlay" style={{ zIndex: 9999 }}>
          <div className="modal-wrapper">
            <div className="modal-content">
              <span className="close-button" onClick={handleClose}>
                &times;
              </span>
              <div className="modal-title-container">
                <div>
                  <h1>{image?.title}</h1>
                </div>
              </div>
              <div className="modal-content-container">
                <div className="modal-image-container">
                  <img src={image?.image} alt={image?.title} style={{ maxWidth: '100%', height: 'auto' }} />
                </div>
              </div>
              {/* Display deletion message */}
              {deleteMessage && <div className="modal-delete-message">{deleteMessage}</div>}
              {/* Add your footer options here */}
              <div className="modal-footer">
                <button onClick={handleDelete}>Delete</button>
                <button onClick={handleClose}>Close</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  );
};

export default DetailImageModal;
