import { useState } from 'react';
import api from '../api';
import { useNavigate } from 'react-router-dom';
import { ACCESS_TOKEN, REFRESH_TOKEN } from '../constants';
import '../styles/UserCredForm.css';

// Route is where we are going, method is whether we are signing up or signing in
// Added email for signin, may want to hide email field for signin
function UserCredForm({route, method}) {
    // Collect what user is typing in
    const [username, setUsername] = useState('')
    const [password, setPassword] = useState('')
    const [email, setEmail] = useState('')
    // Track if loading
    const [loading, setLoading] = useState(false)
    const navigate = useNavigate()

    const methodName = method === 'signin' ? 'signin' : 'signup'

    const handleSubmit = async (e) => {
        setLoading(true);
        e.preventDefault();
    
        try {
            const res = await api.post(route, { username, email, password });
            if (method === 'signin') {
                localStorage.setItem(ACCESS_TOKEN, res.data.access);
                localStorage.setItem(REFRESH_TOKEN, res.data.refresh);
                // Redirect to homepage after successful login
                navigate('/');
            } else {
                navigate('/signin');
            }
        } catch (error) {
            alert(error);
        } finally {
            setLoading(false);
        }
    }
    

    return <form onSubmit= {handleSubmit} className='form-container'>
        <h1>{methodName}</h1>
        <input 
            className='form-input'
            type='text'
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder='Username'
        />
        <input 
            className='form-input'
            type='email'
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder='email'
        />
        <input 
            className='form-input'
            type='password'
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder='Password'
        />
        <button className='form-button' type='submit'>
            {methodName}
        </button>
    </form>
}

export default UserCredForm;