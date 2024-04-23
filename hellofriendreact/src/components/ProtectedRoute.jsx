import { Navigate } from 'react-router-dom';
import { jwtDecode } from 'jwt-decode';
import api from '../api';
import { REFRESH_TOKEN, ACCESS_TOKEN } from '../constants';
import { useState, useEffect } from 'react';

function ProtectedRoute({ children }) {

    // (Custom front end protection) Check if someone is authorized first
	const [isAuthorized, setIsAuthorized] = useState(null);

	useEffect(() => {
	    auth().catch(() => setIsAuthorized(false))
	}, [])

	const refreshToken = async () => {
		const refreshToken = localStorage.getItem(REFRESH_TOKEN)
		try {
			const res = await api.post('/users/token/refresh/', { 
				refresh: refreshToken,
			});
			if (res.status === 200) {
				localStorage.setItem(ACCESS_TOKEN, res.data.access)
				setIsAuthorized(true)
			} else {
				setIsAuthorized(false)
			}

		} catch (error) {
			console.log(error);
			setIsAuthorized(false);
		}
	};

	const auth = async () => {
	    // Check for token
		const token = localStorage.getItem(ACCESS_TOKEN);
		if (!token) {
			setIsAuthorized(false);
			return;
		}
	    // Automatically decode and give access to expiration date
		const decoded = jwtDecode(token);
		const tokenExpiration = decoded.exp;
		const now = Date.now() / 1000;  // Get date in seconds

		if (tokenExpiration < now) {
			await refreshToken();
		} else {
			setIsAuthorized(true);
		}
	}

	if (isAuthorized === null) {
		return <div>Loading...</div>;

	}
 
	return isAuthorized ? children : <Navigate to='/signin' />;

}

export default ProtectedRoute;