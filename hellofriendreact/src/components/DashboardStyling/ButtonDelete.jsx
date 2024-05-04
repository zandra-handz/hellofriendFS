import React, { useState } from 'react';
import { FaTrash } from 'react-icons/fa';
import MessageSave from './MessageSave';
import '/src/styles/OldStyles.css';

const ButtonDelete = ({ onDelete, handleDeleteItem }) => {
    const [confirmationOpen, setConfirmationOpen] = useState(false);
    const [errorMessage, setErrorMessage] = useState('');
    const [successMessage, setSuccessMessage] = useState('');

    const handleConfirmationYes = async () => {
        try {
            await handleDeleteItem(); // Call the handleDeleteItem function passed from parent
            setSuccessMessage('Item deleted successfully!');
            setTimeout(() => {
                setSuccessMessage('');
                onDelete(); // Call the onDelete function after success
            }, 5000); // Clear success message after 5 seconds
        } catch (error) {
            setErrorMessage('Error deleting item.');
        }
        setConfirmationOpen(false);
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
                    <p>Are you sure you want to delete this?</p>
                    <button onClick={handleConfirmationYes}>Yes</button>
                    <button onClick={handleConfirmationNo}>No</button>
                </div>
            )}
            {errorMessage && <MessageSave sentenceObject={{ message: errorMessage }} />}
            {successMessage && <MessageSave sentenceObject={{ message: successMessage }} />}
            <button className="delete-button" onClick={handleButtonClick}><FaTrash /></button>
        </div>
    );
};

export default ButtonDelete;
