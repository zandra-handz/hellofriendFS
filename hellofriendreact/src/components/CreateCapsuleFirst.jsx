import React from 'react';
import CardCreateFirst from './DashboardStyling/CardCreateFirst';
import { FaArrowRight } from 'react-icons/fa';
import useFocusMode from '../hooks/UseFocusMode'; // Import useFocusMode hook

const CreateCapsuleFirst = () => {
  const { focusMode } = useFocusMode(); // Get focus mode from useFocusMode hook

  return (
    <>
      {!focusMode && (
        <div style={helperTextStyle}>Here <FaArrowRight/> </div>
      )}
      <CardCreateFirst
        title="Add your first thought to share with this friend later!"
      />
    </>
  );
};

// Style for the helper text
const helperTextStyle = {
  position: 'fixed',
  top: '6px', // Adjust as needed to position near the top
  left: '5%', // Center horizontally
  transform: 'translateX(-50%)', // Center horizontally
  backgroundColor: 'rgba(0, 0, 0, 0.7)',
  color: 'white',
  padding: '4px 8px', // Padding around the helper text
  borderRadius: '4px', // Border radius
  fontSize: '12px', // Font size of the helper text
  zIndex: 99999,
  animation: 'breathe 3s infinite', // Apply the breathe animation
};

export default CreateCapsuleFirst;
