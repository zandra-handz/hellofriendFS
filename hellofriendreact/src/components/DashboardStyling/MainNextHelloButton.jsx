import React from 'react';
import '/src/styles/OldStyles.css';
import useSelectedFriend from '/src/hooks/UseSelectedFriend'; 
import useThemeMode from '/src/hooks/UseThemeMode';
import { FaArrowRight } from 'react-icons/fa';




const MainNextHelloButton = ({ friendName, futureDate, friendObject }) => {
    const { themeMode } = useThemeMode();
    const { selectedFriend, setFriend } = useSelectedFriend(); 

    const animationDuration = Math.random() * 2 + 1; // Random duration between 1 and 3 seconds
    const animationDelay = Math.random() * 20;// Random delay between 0 and 2 seconds


    const handleButtonClick = () => {
        setFriend(friendObject);
    };

    return (
        <div className={`${themeMode === 'dark' ? 'dark-mode' : ''}`}>
            <button
                className="upcoming-button"
                style={{
                    animation: `pulse ${animationDuration}s infinite alternate`,
                    animationDelay: `${animationDelay}s` // Corrected here
                }}
                onClick={() => setFriend(friendObject)}
            >
                <span className="upcoming-button-text pulsing-text">
                    {friendName}  <FaArrowRight /> {futureDate}
                </span>
            </button>
        </div>
    );
};

export default MainNextHelloButton;