import React, { useState, useEffect } from 'react';

const MessageSave = ({ sentenceObject }) => {
    const [showPopup, setShowPopup] = useState(true);

    useEffect(() => {
        const timer = setTimeout(() => {
            setShowPopup(false);
        }, 3000); // Set the duration for the popup to be visible (in milliseconds)

        return () => {
            clearTimeout(timer);
        };
    }, []);

    return (
        <div className={`popup ${showPopup ? 'show' : 'hide'}`}>
            <div className="popup-content">{sentenceObject.message}</div>
        </div>
    );
};

export default MessageSave;
