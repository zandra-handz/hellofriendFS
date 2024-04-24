import React, { useEffect, useState } from 'react';
import api from '../api';
import CardUneditable from './DashboardStyling/CardUneditable';
import useSelectedFriend from '../hooks/UseSelectedFriend';
import DetailImageModal from './DashboardStyling/DetailImageModal'; 

const FriendImages = () => { 
  const [imagesByCategory, setImagesByCategory] = useState({});
  const [selectedImageId, setSelectedImageId] = useState(null);
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
        // Handle the error, e.g., by setting imagesByCategory to an empty object
        setImagesByCategory({});
      }
    };
  
    fetchData();
  }, [selectedFriend]);
  
  const handleImageClick = (imageId) => {
    setSelectedImageId(imageId);
  };


  return (
    <div>
      {Object.keys(imagesByCategory).length > 0 ? (
        // Iterate through categories
        Object.keys(imagesByCategory).map(category => (
          <div key={category}>
            <CardUneditable title={category}>
              <div className="image-button" style={{ display: 'flex', flexWrap: 'wrap' }}>
                {imagesByCategory[category].map(image => (
                  <div key={image.id} style={{ margin: '10px' }}>
                    <h3>{image.title}</h3>
                    <button
                      onClick={() => handleImageClick(image.id)} // Pass image ID to handleImageClick
                    >
                      <img
                        src={image.image}
                        alt={image.title}
                        style={{ maxWidth: '100px', maxHeight: '100px', objectFit: 'cover' }}
                      />
                    </button>
                  </div>
                ))}
              </div>
            </CardUneditable>
          </div>
        ))
      ) : (
        <p></p>
      )}
      <DetailImageModal
        image={imagesByCategory[selectedImageId]}
        onClose={() => setSelectedImageId(null)} // Reset selectedImageId when modal is closed
      />
    </div>
  );
};

export default FriendImages;
