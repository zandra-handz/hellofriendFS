import React, { useState, useEffect, useRef } from 'react';
import api from '/src/api';
import useAuthUser from '/src/hooks/UseAuthUser';
import useSelectedFriend from '/src/hooks/UseSelectedFriend';
import useThemeMode from '/src/hooks/UseThemeMode';
import Spinner from './Spinner';
import { FaTrash } from 'react-icons/fa';
import '/src/styles/OldStyles.css';
import useCapsuleList from '/src/hooks/UseCapsuleList';

const QuickThoughtCapsuleAddModal = ({ onClose, onSave }) => {
  const { themeMode } = useThemeMode();
  const { selectedFriend } = useSelectedFriend();
  const { capsuleList, setCapsuleList } = useCapsuleList();
  const [loading, setLoading] = useState(true); // State to track loading
  const [textInput, setTextInput] = useState('');
  const [categoryInput, setCategoryInput] = useState('');
  const [categoryLabelValue, setCategoryLabelValue] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const textareaRef = useRef();
  const [textboxPlaceholder, setTextboxPlaceholder] = useState('Start typing your thought here');
  const [nextMeetData, setNextMeetData] = useState('');
  const [categoryLimit, setCategoryLimit] = useState('');
  const [remainingCategories, setRemainingCategories] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [isDeleted, setIsDeleted] = useState(false); 
  const { authUser } = useAuthUser();
  const calculateRemainingCategories = (categoryLimit, capsuleList) => {
    const uniqueCategories = [...new Set(capsuleList.map(capsule => capsule.typedCategory))];
    const uniqueCategoriesCount = uniqueCategories.length;
    console.log("Unique Categories:", uniqueCategories);
    console.log("Unique Categories Count:", uniqueCategoriesCount);
    return categoryLimit - uniqueCategoriesCount;
  };
  
  useEffect(() => {
    if (selectedFriend) {
      fetchInitialData();
    }
  }, [selectedFriend]);
  
  const fetchInitialData = async () => {
    try {
      const [categoryLimitResponse] = await Promise.all([
        api.get(`/friends/${selectedFriend.id}/category-limit/`)
      ]);
      const categoryLimitValue = parseInt(categoryLimitResponse.data.category_limit_formula, 10); // Parse the value to an integer
      console.log("Category Limit Value:", categoryLimitValue);
      const remainingCategoriesCount = calculateRemainingCategories(categoryLimitValue, capsuleList);
      console.log("Remaining Categories Count:", remainingCategoriesCount);
      setCategoryLimit(categoryLimitValue);
      setRemainingCategories(remainingCategoriesCount);
    } catch (error) {
      console.error('Error fetching initial data:', error);
    }
  };
  
  
  


  const handleInputChange = (e) => {
    setTextInput(e.target.value);
  };

  const handleCategoryInputChange = (e) => {
    setCategoryInput(e.target.value);
    setTextboxPlaceholder('Start typing your thought here');
    setSelectedCategory('');
  };

  const handleCategoryChange = async (e) => {
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
  
        // Log the values of selectedCategory and categoryInput
        console.log('Selected Category:', selectedCategory);
        console.log('Category Input:', categoryInput);
  
        // Add the saved capsule to the capsuleList
        setCapsuleList(prevCapsuleList => [
          ...prevCapsuleList,
          {
            id: response.data.id,
            typedCategory: selectedCategory || categoryInput, // Make sure typedCategory is set
            capsule: textInput  
          }
        ]);
  
        // Clear input fields and set success message
        setTextInput('');
        setCategoryInput('');
        setCategoryLabelValue('');
        setSelectedCategory('');
        setSuccessMessage('Idea saved successfully!');
        onSave(textInput);
      }
    } catch (error) {
      console.error('Error creating idea:', error);
    }
  };
  
  

  const handleTrashClick = async (capsuleId) => {
    try {
      await api.delete(`/friends/${selectedFriend.id}/thoughtcapsule/${capsuleId}/`);
  
      // Remove the deleted capsule from the capsuleList
      setCapsuleList(prevCapsuleList => prevCapsuleList.filter(capsule => capsule.id !== capsuleId));
  
      setSuccessMessage('Idea deleted successfully!');
      setIsDeleted(true); 
      setTimeout(() => {
        setIsDeleted(false);  
      }, 3000);
    } catch (error) {
      console.error('Error deleting capsule:', error);
    }
  };
  

  console.log("Capsule List:", capsuleList);
 
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
                <h1>Add a thought</h1>
                <h1>(categories left: {remainingCategories}) </h1>
              </div>
            </div>
            <div className="modal-content-container">
              <div className="modal-input-container">
                {(remainingCategories > 0 || selectedCategory) && (
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
                {remainingCategories > 0 && (
                  <div className="input-container">
                    <label htmlFor="newCategory">New Category </label>
                    <input
                      type="text"
                      id="newCategory"
                      value={categoryInput}
                      onChange={handleCategoryInputChange}
                      placeholder="examples: 'work news', 'hobbies', 'family', 'shared interests' "
                    />
                  </div>
                )}
                {capsuleList.length > 0 && (
                  <div className="input-container">
                    <label htmlFor="category">Or </label>
                    <select
                      id="category-select"
                      className="modal-select"
                      value={selectedCategory}
                      onChange={handleCategoryChange}
                    >
                      <option value="">Add to existing category</option>
                      {/* Extract unique categories from capsuleList */}
                      {[...new Set(capsuleList.map(capsule => capsule.typedCategory))].map((categoryInfo) => (
                        <option key={categoryInfo} value={categoryInfo}>
                          {categoryInfo}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
  
                {selectedCategory && (
                  <div className="capsules-container">
                    {capsuleList
                      .filter((capsule) => capsule.typedCategory === selectedCategory)
                      .map((capsule) => (
                        <div className="label-container" id="category-notes" key={capsule.id} style={{ display: 'flex' }}>
                          <div>{capsule.capsule}</div>
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
    </div>
  );
};

export default QuickThoughtCapsuleAddModal;
