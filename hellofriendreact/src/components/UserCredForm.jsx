import { useState } from 'react';
import api from '../api';
import { useNavigate } from 'react-router-dom';
import { ACCESS_TOKEN, REFRESH_TOKEN } from '../constants';
import SpinnerSignin from './SpinnerSignin'; // Import your Spinner component here
import '../styles/UserCredForm.css';

function UserCredForm({ route, method }) {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [email, setEmail] = useState(''); // Declare email state variable
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    const methodName = method === 'signin' ? 'signin' : 'signup';

    const handleSubmit = async (e) => {
        setLoading(true);
        e.preventDefault();

        try {
            const res = await api.post(route, { username, email, password });
            if (method === 'signin') {
                localStorage.setItem(ACCESS_TOKEN, res.data.access);
                localStorage.setItem(REFRESH_TOKEN, res.data.refresh);
                navigate('/');
            } else {
                // Show success message for signup
                alert('Sign up successful! Please sign in.');
                navigate('/signin');
            }
        } catch (error) {
            if (error.response.status === 401) {
                // Show error message for username and password mismatch
                alert('Oops! Username and password do not match. Please try again!');
            } else {
                // Show other error messages
                alert('An error occurred. Please try again later.');
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className='form-container'>
            {loading ? (
                <SpinnerSignin /> // Render the Spinner component when loading is true
            ) : (
                <form onSubmit={handleSubmit}>
                    <div className='form-header'>
                        <h1>hellofr::nd</h1>
                        <h3>{methodName}</h3>
                    </div> 
                    <input
                        className='form-input'
                        type='text'
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        placeholder='Username'
                        required // Make the username field required
                    />
                    {method === 'signup' && (
                        <input
                            className='form-input'
                            type='email'
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder='Email'
                            required // Make the email field required for signup
                        />
                    )}
                    <input
                        className='form-input'
                        type='password'
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder='Password'
                        required // Make the password field required
                    />
                    <button className='form-button' type='submit'>
                        {methodName}
                    </button>
                </form>
            )}
        </div>
    );
}

export default UserCredForm;
