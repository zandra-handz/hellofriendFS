import React, { useState, useEffect, useRef } from 'react';
import api from '/src/api';
import useAuthUser from '/src/hooks/UseAuthUser';
import useSelectedFriend from '/src/hooks/UseSelectedFriend';
import useThemeMode from '/src/hooks/UseThemeMode';
import Spinner from './Spinner';
import { FaTrash } from 'react-icons/fa';
import '/src/styles/OldStyles.css';

const QuickThoughtCapsuleAddModal = ({ onClose, onSave }) => {
  const { themeMode } = useThemeMode();
  const [loading, setLoading] = useState(true); // State to track loading
  const [textInput, setTextInput] = useState('');
  const [categoryInput, setCategoryInput] = useState('');
  const [categoryLabelValue, setCategoryLabelValue] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const textareaRef = useRef();
  const [textboxPlaceholder, setTextboxPlaceholder] = useState('Start typing your thought here');
  const [nextMeetData, setNextMeetData] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [thoughtCapsules, setThoughtCapsules] = useState([]);
  const [isDeleted, setIsDeleted] = useState(false); 
  const { authUser } = useAuthUser();
  const { selectedFriend } = useSelectedFriend();

  useEffect(() => {
    if (selectedFriend) {
      fetchUpdatedData();
    }
  }, [selectedFriend]);

  

  const fetchUpdatedData = async () => {
    try {
      const [capsulesResponse, nextMeetResponse] = await Promise.all([
        api.get(`/friends/${selectedFriend.id}/thoughtcapsules/add/`),
        api.get(`/friends/${selectedFriend.id}/next-meet/`)
      ]);
      setThoughtCapsules(capsulesResponse.data);
      setNextMeetData(nextMeetResponse.data[0]);
      setTimeout(() => {
        setSuccessMessage('');
        setLoading(false); // Set loading to false when data is loaded
      }, 2000);
    } catch (error) {
      console.error('Error fetching updated data:', error);
    }
  };

  const handleInputChange = (e) => {
    console.log('textInput updated:', e.target.value);
    setTextInput(e.target.value);
  };

  const handleCategoryInputChange = (e) => {
    console.log('categoryInput updated:', e.target.value);
    setCategoryInput(e.target.value);
    setTextboxPlaceholder('Start typing your thought here');
    setSelectedCategory('');
  };

  const handleCategoryChange = async (e) => {
    console.log('selectedCategory updated:', e.target.value);
    setSelectedCategory(e.target.value);
    setCategoryLabelValue(e.target.value ? `${e.target.value}` : '');
    setTextboxPlaceholder(`add to ${e.target.value}`);
    setCategoryInput('');
    const textareaElement = textareaRef.current;

    if (textareaElement && textareaElement.offsetWidth && textareaElement.offsetHeight) {
      textareaRef.current.focus();
    }
  };

  const handleSave = async () => {
    try {
      if (selectedFriend) {
        const requestData = {
          user: authUser.user.id,
          friend: selectedFriend.id,
          typed_category: selectedCategory || categoryInput,
          capsule: textInput,
        };

        const response = await api.post(`/friends/${selectedFriend.id}/thoughtcapsules/add/`, requestData);

        setTextInput('');
        setCategoryInput('');
        setCategoryLabelValue('');
        setSelectedCategory('');
        setSuccessMessage('Idea saved successfully!');
        fetchUpdatedData(); // Fetch updated data after saving the idea
        onSave(textInput);
      }
    } catch (error) {
      console.error('Error creating idea:', error);
    }
  };

  const handleTrashClick = async (capsuleId) => {
    try {
      await api.delete(`/friends/${selectedFriend.id}/thoughtcapsule/${capsuleId}/`);
      
      setSuccessMessage('Idea deleted successfully!');
      fetchUpdatedData();
      setIsDeleted(true); 
      setTimeout(() => {
        setIsDeleted(false);  
      }, 3000);  
    } catch (error) {
      console.error('Error deleting capsule:', error);
    }
  };

  return (
    <div className={`${themeMode === 'dark' ? 'dark-mode' : ''}`}>
      {loading ? (
        <div className="spinner-container">
          <Spinner />
        </div>
      ) : (
        <div className="modal-overlay" style={{ zIndex: 9999 }}> 
          <div className="modal-wrapper">
            <div className="modal-content">
              <span className="close-button" onClick={onClose}>
                &times;
              </span>
              <div className="modal-title-container">
                <div>
                  <h1>Add a thought ({nextMeetData.category_activations_left} left) </h1>
                </div>
              </div>
              <div className="modal-content-container">
                <div className="modal-input-container">
                  {(nextMeetData.category_activations_left > 0 || selectedCategory) && (
                    <div className="input-container">
                      <textarea
                        id="notes"
                        ref={textareaRef} 
                        autoFocus
                        value={textInput}
                        placeholder={textboxPlaceholder}
                        onChange={handleInputChange}
                      />
                    </div>
                  )}
                </div>
                <div className="modal-input-container">
                  {nextMeetData.category_activations_left > 0 && (
                    <div className="input-container">
                      <label htmlFor="newCategory">Category </label>
                      <input
                        type="text"
                        id="newCategory"
                        value={categoryInput}
                        onChange={handleCategoryInputChange}
                        placeholder="examples: 'work news', 'hobbies', 'family', 'shared interests' "
                      />
                    </div>
                  )}
                  {nextMeetData.active_categories && (
                    <div className="input-container">
                      <label htmlFor="category"> </label>
                      <select id="category-select" className="modal-select" value={selectedCategory} onChange={handleCategoryChange}>
                        <option value="">Add to existing category</option>
                        {nextMeetData.active_categories.map((categoryInfo) => (
                          <option key={categoryInfo} value={categoryInfo}>
                            {categoryInfo}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}

                  {selectedCategory.length > 0 && (
                    <div className="capsules-container">
                      {thoughtCapsules
                        .filter((capsule) => capsule.category === selectedCategory || capsule.typed_category === selectedCategory)
                        .map((capsule) => (
                          <div className="label-container" id="category-notes" key={capsule.id} style={{ display: 'flex' }}>
                            {capsule.capsule} 
                            <div className="trash-container">
                              <button onClick={() => handleTrashClick(capsule.id)}>
                                <FaTrash />
                              </button>
                            </div>
                          </div>
                        ))} 
                    </div>
                  )}
                </div>
                <div className="modal-input-container">
                  {successMessage && <p className="success-message">{successMessage}</p>}
                </div>
                <div className="modal-save-button-container">
                  <button className="modal-save-button" onClick={handleSave} disabled={(!selectedCategory || !categoryInput) && !textInput}>
                    Save
                  </button>
                  {isDeleted && <p className="delete-message">Capsule deleted!</p>}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default QuickThoughtCapsuleAddModal;
