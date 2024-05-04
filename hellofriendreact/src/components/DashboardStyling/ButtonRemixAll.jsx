import React, { useState } from 'react';
import api from '/src/api';
import { FaRecycle } from 'react-icons/fa';
import MessageSave from './MessageSave';
import '/src/styles/OldStyles.css';

const ButtonRemixAll = ({ onRemix }) => {
    const [confirmationOpen, setConfirmationOpen] = useState(false);
    const [errorMessage, setErrorMessage] = useState('');
    const [successMessage, setSuccessMessage] = useState('');

    const handleRemixAllNextMeets = async () => {
        try {
            await api.post('/friends/remix/all/');
            setSuccessMessage('Friend dates remixed!');
            setTimeout(() => {
                setSuccessMessage('');
                onRemix(); // Call the onRemix function after success
            }, 5000); // Clear success message after 5 seconds
        } catch (error) {
            setErrorMessage('Error remixing all next meets.');
        }
    };

    const handleConfirmationYes = () => {
        setConfirmationOpen(false);
        handleRemixAllNextMeets();
    };

    const handleConfirmationNo = () => {
        setConfirmationOpen(false);
    };

    const handleButtonClick = () => {
        setConfirmationOpen(true);
    };

    return (
        <div>
            {confirmationOpen && (
                <div className="confirmation-popup">
                    <p>Are you sure you want to remix all next meets?</p>
                    <button onClick={handleConfirmationYes}>Yes</button>
                    <button onClick={handleConfirmationNo}>No</button>
                </div>
            )}
            {errorMessage && <MessageSave sentenceObject={{ message: errorMessage }} />}
            {successMessage && <MessageSave sentenceObject={{ message: successMessage }} />}
            <button className="mass-function-button" onClick={handleButtonClick}><FaRecycle /></button>
        </div>
    );
};

export default ButtonRemixAll;
