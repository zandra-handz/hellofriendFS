import React, { useState } from 'react';
import useThemeMode from '/src/hooks/UseThemeMode';
import '/src/styles/OldStyles.css';
 


const ButtonExpandAll = ({ onClick, expandText, collapseText }) => {
  const { themeMode } = useThemeMode();
  const [expanded, setExpanded] = useState(false);


  const handleClick = () => {
    setExpanded(!expanded);
    onClick(!expanded);
  };

  return (
    <div className={`${themeMode === 'dark' ? 'dark-mode' : ''}`}> 
        <button className='mass-function-button' onClick={handleClick}>{expanded ? collapseText : expandText}</button>
         
    </div>
  );
};

export default ButtonExpandAll;


 