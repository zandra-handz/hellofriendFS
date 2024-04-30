// CardInnerEditMode.jsx
import React from 'react';
import { FaWrench } from 'react-icons/fa';

const CardInnerEditMode = ({ isEditMode, onToggleEditMode, onSubmit, data, handleInputChange, editedEffortRequired, editedPriorityLevel }) => {
  return (
    <div>
      {isEditMode && data ? (
        <div>
          <h5>Edit Friend Settings</h5>
          <div>
            <label>Effort Required:</label>
            <input type="range" min="1" max="5" value={editedEffortRequired} name="effort" onChange={handleInputChange} />
          </div>
          <div>
            <label>Priority Level:</label>
            <input type="range" min="1" max="3" value={editedPriorityLevel} name="priority" onChange={handleInputChange} />
          </div>
          <div>
            <button onClick={onSubmit}>Submit</button>
          </div>
        </div>
      ) : (
        <div>
          {/* Display the data when not in edit mode */}
          <h5>Friend Settings</h5>
          <p>Effort Required: {data.effort_required}</p>
          <p>Priority Level: {data.priority_level}</p>
        </div>
      )}
      {/* Wrench button for toggling edit mode */}
      <div className="edit-card-wrench-button" onClick={onToggleEditMode}>
        <FaWrench />
      </div>
    </div>
  );
};

export default CardInnerEditMode;
