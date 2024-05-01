import React from 'react';
import '/src/styles/OldStyles.css';

const GridOneOrTwoColsAnyRows = ({ children }) => {
  return (
    <div className="grid">
      {children}
    </div>
  );
};

export default GridOneOrTwoColsAnyRows;
