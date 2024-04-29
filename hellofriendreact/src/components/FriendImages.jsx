import React, { useEffect, useState } from 'react';
import api from '../api';
import CardUneditable from './DashboardStyling/CardUneditable';
import useSelectedFriend from '../hooks/UseSelectedFriend';
import DetailImageModal from './DashboardStyling/DetailImageModal';  
import TabSpinner from './DashboardStyling/TabSpinner';

const FriendImages = () => {
  const [imagesByCategory, setImagesByCategory] = useState({});
  const [selectedImageId, setSelectedImageId] = useState(null); // State to store the selected image ID
  const { selectedFriend } = useSelectedFriend();

  useEffect(() => {
    const fetchData = async () => {
      try {
        if (selectedFriend) {
          const imagesResponse = await api.get(`/friends/${selectedFriend.id}/images/by-category/`);
          setImagesByCategory(imagesResponse.data);
        }
      } catch (error) {
        console.error('Error fetching data:', error);
        setImagesByCategory({});
      }
    };
  
    fetchData();
  }, [selectedFriend]);
  
  const handleImageClick = (imageId) => {
    setSelectedImageId(imageId); // Set the selected image ID
  };

  return (
    <div>
      {Object.keys(imagesByCategory).length > 0 && (
        Object.keys(imagesByCategory).map(category => (
          <div key={category}>
            <CardUneditable title={category}>
              <div className="image-button" style={{ display: 'flex', flexWrap: 'wrap' }}>
                {imagesByCategory[category].map(image => (
                  <div key={image.id} style={{ margin: '10px' }}>
                    <h3>{image.title}</h3>
                    <div onClick={() => handleImageClick(image.id)}>
                      <img
                        src={image.image}
                        alt={image.title}
                        style={{ maxWidth: '100px', maxHeight: '100px', objectFit: 'cover' }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </CardUneditable>
          </div>
        ))
      )}
      <DetailImageModal
        imageId={selectedImageId} // Pass the selected image ID as prop
        onClose={() => setSelectedImageId(null)} // Reset selectedImageId when modal is closed
      />
    </div>
  );
};

export default FriendImages;
