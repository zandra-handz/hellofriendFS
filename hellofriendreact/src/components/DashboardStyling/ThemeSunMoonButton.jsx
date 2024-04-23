import React, { useState } from 'react';
import { FaSun, FaMoon } from 'react-icons/fa';
import useThemeMode from '/src/hooks/UseThemeMode';
import '/src/styles/OldStyles.css';

const ThemeSunMoonButton = () => {
    const { themeMode, toggleThemeMode } = useThemeMode();

    const handleToggleMode = () => {
        toggleThemeMode();
    };

    const icon = themeMode === 'light' ? <FaSun /> : <FaMoon />;

    const helperText = themeMode === 'light' ? 'Light mode' : 'Dark mode';

    return (
        <button className="header-button" onClick={handleToggleMode} title={helperText}>
            {icon}
        </button>
    );
};

export default ThemeSunMoonButton;
