import React, { useEffect, useState } from 'react';
import api from '../api';
import CardExpandAndConfig from './DashboardStyling/CardExpandAndConfig';
import Spinner from './DashboardStyling/Spinner';
import useAuthUser from '../hooks/UseAuthUser';
import { FaWrench } from 'react-icons/fa';

const UserProfile = () => {
  const [data, setData] = useState(null);
  const [isEditMode, setIsEditMode] = useState(false);
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [dateOfBirth, setDateOfBirth] = useState('');
  const [gender, setGender] = useState('');
  const [expanded, setExpanded] = useState(false); // State for managing expanded/collapsed state
  const { authUser } = useAuthUser();

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await api.get(`/users/${authUser.user.id}/profile/`);
        setData(response.data);
        setFirstName(response.data.first_name);
        setLastName(response.data.last_name);
        setDateOfBirth(response.data.date_of_birth);
        setGender(response.data.gender);
      } catch (error) {
        console.error('Error fetching user profile:', error);
      }
    };
    fetchData();
  }, []);

  const toggleEditMode = () => {
    setIsEditMode(prevMode => !prevMode);
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    // Update corresponding state based on input field name
    switch (name) {
      case 'firstName':
        setFirstName(value);
        break;
      case 'lastName':
        setLastName(value);
        break;
      case 'dateOfBirth':
        setDateOfBirth(value);
        break;
      case 'gender':
        setGender(value);
        break;
      default:
        break;
    }
  };

  const handleSubmit = async () => {
    try {
      await api.put(`/users/${authUser.user.id}/profile/update/`, {
        user: authUser.user.id,
        first_name: firstName,
        last_name: lastName,
        date_of_birth: dateOfBirth,
        gender: gender
      });
      // Assuming the update is successful, we can set edit mode to false to switch back to view mode
      setIsEditMode(false);
    } catch (error) {
      console.error('Error updating user profile:', error);
    }
  };

  return (
    <CardExpandAndConfig
      title="User Profile"
      expanded={expanded}
      onEditButtonClick={() => setExpanded(prevExpanded => !prevExpanded)}
    >
      <>
        {expanded ? (
          <div>
            <div className="edit-card-header">
              <h5></h5>
              <button className="edit-button" onClick={toggleEditMode}>
                <FaWrench />
              </button>
            </div>
            {isEditMode ? (
              <div>
                <div>
                  <label>
                    First Name:
                    <input type="text" name="firstName" value={firstName} onChange={handleInputChange} />
                  </label>
                </div>
                <div>
                  <label>
                    Last Name:
                    <input type="text" name="lastName" value={lastName} onChange={handleInputChange} />
                  </label>
                </div>
                <div>
                  <label>
                    Date of Birth:
                    <input type="date" name="dateOfBirth" value={dateOfBirth} onChange={handleInputChange} />
                  </label>
                </div>
                <div>
                  <label>
                    Gender:
                    <select name="gender" value={gender} onChange={handleInputChange}>
                      <option value="NB">Non-Binary</option>
                      <option value="M">Male</option>
                      <option value="F">Female</option>
                      <option value="O">Other</option>
                      <option value="No answer">Uninterested in answering this</option>
                    </select>
                  </label>
                </div>
                <div>
                  <button onClick={handleSubmit}>Submit</button>
                </div>
              </div>
            ) : (
              <div>
                <p>First Name: {firstName}</p>
                <p>Last Name: {lastName}</p>
                <p>Date of Birth: {dateOfBirth}</p>
                <p>Gender: {gender}</p>
              </div>
            )}
          </div>
        ) : (
          <div>
            {data ? (
              <div>
                <p>First Name: {firstName}</p>
                <p>Last Name: {lastName}</p>
                <p>Date of Birth: {dateOfBirth}</p>
                <p>Gender: {gender}</p>
              </div>
            ) : (
              <Spinner />
            )}
          </div>
        )}
      </>
    </CardExpandAndConfig>
  );
};

export default UserProfile;
