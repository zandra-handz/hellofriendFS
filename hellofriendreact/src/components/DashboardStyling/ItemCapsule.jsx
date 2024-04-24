
import React from 'react';
import useThemeMode from '/src/hooks/UseThemeMode';
import { FaLeaf } from 'react-icons/fa';
import '/src/styles/OldStyles.css';

const ItemCapsule = ({ capsule }) => {
    const { themeMode } = useThemeMode();

  return (
    <div className={`${themeMode === 'dark' ? 'dark-mode' : ''}`}>
        <div className="capsule-item">
        <FaLeaf />
        <p>{capsule}</p>
        </div>
    </div>
  );
};

export default ItemCapsule;