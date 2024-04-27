import React, { useState, useEffect, useRef } from 'react';
import api from '/src/api'; 
import useAuthUser from '/src/hooks/UseAuthUser';
import useSelectedFriend from '/src/hooks/UseSelectedFriend';
import useCapsuleList from '/src/hooks/UseCapsuleList'; 
import useThemeMode from '/src/hooks/UseThemeMode';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import '/src/styles/OldStyles.css';

const AddHelloModal = ({ onClose, onSave }) => {
  const { themeMode } = useThemeMode();
  const [textInput, setTextInput] = useState('');
  const [selectedDate, setSelectedDate] = useState(new Date()); 
  const [typeChoices, setTypeChoices] = useState([]);
  const [locationLabelValue, setLocationLabelValue] = useState('');
  const [locationInput, setLocationInput] = useState('');
  const [locationNameInput, setLocationNameInput] = useState('');
  const [selectedLocation, setSelectedLocation] = useState('');
  const [selectedLocationName, setSelectedLocationName] = useState('');
  const [capsuleLabelValue, setCapsuleLabelValue] = useState('');
  const [selectedTypeCapsule, setSelectedTypeCapsule] = useState('');
  const [selectedCapsule, setSelectedCapsule] = useState('');
  const [selectedCapsules, setSelectedCapsules] = useState([]);
  const [deleteChoice, setDeleteChoice] = useState(false);

  const [selectedType, setSelectedType] = useState('');
  const [locationData, setLocationData] = useState([]);
  const textareaRef = useRef();
  const [textboxPlaceholder, setTextboxPlaceholder] = useState('Start typing your thought here');
  
  const [ideaLimit, setIdeaLimit] = useState('');
  const [capsuleData, setCapsuleData] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [shouldClose, setShouldClose] = useState(false);
  const { selectedFriend } = useSelectedFriend();
  const { capsuleList, setCapsuleList } = useCapsuleList(); // Destructure fetchCapsuleList from the hook
  const { authUser } = useAuthUser();

  const handleInputChange = (e) => {
    setTextInput(e.target.value);
  };

  const addSelectedType = (e) => {
    setSelectedType(e.target.value);
  };

  const handleLocationInputChange = (e) => {
    setLocationInput(e.target.value);
    setTextboxPlaceholder('Location address');
    setSelectedLocation('');
  };

  const handleLocationNameInputChange = (e) => {
    setLocationNameInput(e.target.value);
    setTextboxPlaceholder('Location name');
    setSelectedLocation('');
  };

  const handleLocationChange = (e) => {
    const selectedValue = e.target.value;
    setSelectedLocation(selectedValue); // Set selected location
    setLocationLabelValue(selectedValue || ''); // Set location label value based on the selected location
    setTextboxPlaceholder(`add to ${selectedValue || locationInput || locationNameInput}`);
    setLocationNameInput('');
    setLocationInput('');
  };
  
  
  useEffect(() => {
    console.log("Location Data:", locationData); // Log locationData
  }, [locationData]);

  const handleCheckboxCapsuleChange = (capsuleInfo) => {
    console.log('Capsule Info:', capsuleInfo); // Added console.log statement
  
    setSelectedCapsules((prevSelectedCapsules) => {
      const isCapsuleSelected = prevSelectedCapsules.some((item) => item.id === capsuleInfo.id);
  
      if (isCapsuleSelected) {
        return prevSelectedCapsules.filter((item) => item.id !== capsuleInfo.id);
      } else {
        return [...prevSelectedCapsules, { ...capsuleInfo, typed_category: capsuleInfo.typedCategory }];
      }
    });
  
    setTextboxPlaceholder(`add to ${capsuleInfo.capsule}`);
    setCapsuleLabelValue(capsuleInfo.id ? `${capsuleInfo.id}` : '');
  };

  const handleCapsuleChange = async (e) => {
    setSelectedCapsule(e.target.value);
    setCapsuleLabelValue(e.target.value ? `${e.target.value}` : '');
    setTextboxPlaceholder(`add to ${e.target.value}`);
    setLocationInput('');

    const textareaElement = document.getElementById('capsules');

    if (textareaElement && textareaElement.offsetWidth && textareaElement.offsetHeight) {
      textareaRef.current.focus();
    }
  };

  const handleDateChange = (date) => {
    setSelectedDate(date);
  };

  const fetchCapsuleListData = async () => {
    try {
      if (selectedFriend) {
        const response = await api.get(`/friends/${selectedFriend.id}/thoughtcapsules/`);
        const capsuleData = response.data;
        const formattedCapsuleList = capsuleData.map(capsule => ({
          id: capsule.id,
          typedCategory: capsule.typed_category,
          capsule: capsule.capsule
        }));
        setCapsuleList(formattedCapsuleList);
      }
    } catch (error) {
      console.error('Error fetching capsule list:', error);
    }
  };

  const handleSave = async () => {
    try {
      if (selectedFriend) {
        const formattedDate = selectedDate.toISOString().split('T')[0];
        const capsulesDictionary = {};

        selectedCapsules.forEach(capsule => {
          capsulesDictionary[capsule.id] = {
            typed_category: capsule.typed_category,
            capsule: capsule.capsule,
          };
        });

        const requestData = {
          user: authUser.user.id,
          friend: selectedFriend.id,
          type: selectedType,
          typed_location: locationInput,
          location_name: selectedLocationName || locationNameInput,
          location: selectedLocation,
          date: formattedDate,
          thought_capsules_shared: capsulesDictionary,
          delete_all_unshared_capsules: deleteChoice,
        };

        const response = await api.post(`/friends/${selectedFriend.id}/helloes/add/`, requestData);

        // Call the fetchCapsuleList function to refetch the capsule list data after saving
        fetchCapsuleListData();

        setIdeaLimit('limit feature disabled');
        setTextInput('');
        setLocationInput('');
        setLocationNameInput('');
        setCapsuleLabelValue('');
        setSelectedCapsule('');
        setLocationLabelValue('');
        setSelectedLocation('');
        setSuccessMessage('Hello saved successfully!');
        setShouldClose(true);

        setTimeout(() => {
          setSuccessMessage('');
        }, 4000);

        setTimeout(() => {
          setShouldClose((prevShouldClose) => {
            if (prevShouldClose) {
              onClose();
            }
            return prevShouldClose;
          });
        }, 4000);

        onSave(textInput);
      }
    } catch (error) {
      console.error('Error creating idea:', error);
    }
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        if (selectedFriend) {
          const response = await api.get(`/friends/${selectedFriend.id}/thoughtcapsules/`);
          setCapsuleData(response.data);
        }
      } catch (error) {
        console.error('Error fetching data:', error);
      }
      console.log('Capsule data:', {capsuleData});
    };

    fetchData();
  }, [selectedFriend]);

  useEffect(() => {
    const fetchTypeChoices = async () => {
      try {
        const response = await api.get('friends/dropdown/hello-type-choices/');
        setTypeChoices(response.data.type_choices);
      } catch (error) {
        console.error('Error fetching type choices:', error);
      }
    };

    fetchTypeChoices();
  }, []);

  useEffect(() => {
    const fetchLimit = async () => {
      try {
        if (selectedFriend) { 

          setIdeaLimit('none');
        }
      } catch (error) {
        console.error('Error fetching limit:', error);
      }
    };

    fetchLimit();
  }, [selectedFriend]);

  const fetchData = async () => {
    try {
      if (selectedFriend) {
        const response = await api.get(`/friends/dropdown/all-user-locations/`);
        setLocationData(response.data);
  
        // Set initial location label value based on the first location in the data
        if (response.data.length > 0) {
          setLocationLabelValue(response.data[0].address); // Set to the first address, for example
        }
  
        console.log("Location Data:", response.data); // Log locationData after setting state
      }
    } catch (error) {
      console.error('Error fetching data:', error);
    }
  };
  

  const fetchUpdatedData = async () => {
    try {
      await fetchData();
      setTimeout(() => {
        setSuccessMessage('');
      }, 2000);
    } catch (error) {
      console.error('Error fetching updated data:', error);
    }
  };

  useEffect(() => {
    fetchUpdatedData(); // Fetch initial data
  }, [selectedFriend]);

  return (
    <div className={`${themeMode === 'dark' ? 'dark-mode' : ''}`}>
      <div className={`modal-overlay ${successMessage ? 'success-mode' : ''}`}>
        <div className="modal-wrapper">
          {successMessage && (
            <div className="success-message-container">
              <div className="success-message-content">
                <p className="success-message">{successMessage}</p>
              </div>
            </div>
          )}
          <div className={`modal-content ${successMessage ? 'success-mode' : ''}`}>

            <span className="close-button" onClick={() => {
              setShouldClose(false);
              onClose();
            }}>
              &times;
            </span>
            <div className="modal-content-container">
              <div>
                <h1>Add a hello! </h1>
              </div>
              <div>

              </div>
              <div className="modal-input-container">
                {(ideaLimit.remaining_notes > 0 || selectedCapsule) && (
                  <div className="input-container">
                    <textarea
                      id="notes"
                      ref={textareaRef} 
                      value={textInput}
                      placeholder={textboxPlaceholder}
                      onChange={handleInputChange}
                    />
                  </div>
                )}
              </div>
            </div>
            <div className="modal-content-container">
              <div className="modal-input-container">
                <div className="input-container">
                  <label htmlFor="date">Date  </label>
                  <DatePicker
                    id="date"
                    selected={selectedDate}
                    minWidth="100px"
                    onChange={handleDateChange}
                    dateFormat="yyyy-MM-dd"
                  />
                  <label htmlFor="type">Type </label>
                  <select
                    id="type"
                    autoFocus
                    value={selectedType}
                    onChange={(e) => setSelectedType(e.target.value)}
                  >
                    <option value="">Select a type</option>
                    {typeChoices.map((type, index) => (
                      <option key={index} value={type}>
                        {type}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="input-container">
                  <label htmlFor="newLocationName">Location </label>
                  <input
                    type="text"
                    id="newLocationName"
                    value={locationNameInput}
                    onChange={handleLocationNameInputChange}
                    placeholder="name"
                  />
                </div>
                <div className="input-container">
                  <label htmlFor="newLocation">Address </label>
                  <input
                    type="text"
                    id="newLocation"
                    value={locationInput}
                    onChange={handleLocationInputChange}
                    placeholder="(leave empty to keep address unvalidated)"
                  />
                </div>   
                {locationData.length > 0 && (
                  <div className="input-container">
                    <label htmlFor="location"> </label>
                    <select
                      id="location-select"
                      className="modal-select"
                      value={selectedLocation}
                      onChange={handleLocationChange} // Ensure this is correctly bound
                    >
                      <option value="">Been here before: </option>
                      {locationData.map((locationInfo) => (
                        <option key={locationInfo.title} value={locationInfo.id || ''}>
                          {locationInfo.title} {locationInfo.address || 'No address'}
                        </option>
                      ))}
                    </select>

                  </div>
                )}


                {capsuleList.length > 0 && (
                  <div>
                    {Object.entries(capsuleList.reduce((acc, capsule) => {
                      // Check if the category already exists in the accumulator
                      if (!acc[capsule.typedCategory]) {
                        acc[capsule.typedCategory] = []; // If not, create a new category array
                      }
                      // Push the capsule to the corresponding category array
                      acc[capsule.typedCategory].push(capsule);
                      return acc;
                    }, {})).map(([category, categoryCapsules]) => (
                      <div key={category}>
                        <h2>{category}</h2>
                        <div className="scrollable-container">
                          {categoryCapsules.map((capsuleInfo) => (
                            <div key={capsuleInfo.id} className="capsule-item">
                              <label htmlFor={capsuleInfo.id} className="scrollable-label">
                                <div className="checkbox-container">
                                  <input
                                    type="checkbox"
                                    id={capsuleInfo.id} // Ensure each checkbox has a unique id
                                    value={capsuleInfo.id}
                                    checked={selectedCapsules.some((item) => item.id === capsuleInfo.id)}
                                    onChange={() => handleCheckboxCapsuleChange(capsuleInfo)}
                                  />
                                </div> 
                                <div>
                                  <p>{capsuleInfo.capsule}</p>
                                </div>
                              </label>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}



                {selectedCapsule.length > 0 && (
                  <div className="input-container">
                    {capsuleData
                      .filter((capsuleInfo) => capsuleInfo.key === selectedCapsule)
                      .map((capsuleInfo) => (
                        <div className="label-container" id="capsules" key={capsuleInfo.key}>
                          <p>{capsuleInfo.value}</p>
                        </div>
                      ))}
                  </div>
                )}
              </div>
              <div className="modal-input-container">
                {successMessage && (
                  <div className="success-message-container">
                    <div className="success-message-content">
                      <p className="success-message">{successMessage}</p>
                      <button className="close-success-button" onClick={() => setSuccessMessage('')}>
                        Close
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
            <div className="modal-save-button-container">
              <button className="modal-save-button" onClick={handleSave} disabled={(!selectedType) || (!selectedType && !selectedLocation && (!locationInput && !locationNameInput)) || (!selectedLocation && (!locationInput && !locationNameInput))}>
                Save
              </button> 
              {/* Checkbox to set deleteChoice state */}
              {(selectedType && (selectedLocation || locationInput || locationNameInput)) && (
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={deleteChoice}
                    onChange={(e) => setDeleteChoice(e.target.checked)}
                    className="checkbox-input"
                  />
                  Delete choice
                </label>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AddHelloModal;
