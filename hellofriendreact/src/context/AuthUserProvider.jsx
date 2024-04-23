import React, { createContext, useState, useEffect } from "react";
import api from "../api";
import { ACCESS_TOKEN } from '../constants';

const AuthUserContext = createContext({});

export const AuthUserProvider = ({ children }) => {
  const [authUser, setAuthUser] = useState({
    user: null,
    credentials: {
      id: null,
      username: null,
      password: null,
      token: localStorage.getItem(ACCESS_TOKEN), // Initialize token from localStorage
    },
  });

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const response = await api.get(`/users/get-current/`);
        console.log('Auth Provider Current User Data:', response.data);
        setAuthUser(prevAuthUser => ({
          user: response.data,
          credentials: {
            ...prevAuthUser.credentials,
            token: localStorage.getItem(ACCESS_TOKEN), // Update token from localStorage
          },
        }));
      } catch (error) {
        console.error("Error fetching user:", error);
        setAuthUser(prevAuthUser => ({
          ...prevAuthUser,
          user: null,
        }));
      }
    };

    // Fetch user on component mount
    fetchUser();
  }, []);

  const setUser = (user, credentials) => {
    // Update the credentials
    setAuthUser(prevAuthUser => ({
      user: user,
      credentials: {
        ...prevAuthUser.credentials,
        ...credentials,
      },
    }));
  };

  console.log('AuthUser Provider All Values:', { authUser });

  return (
    <AuthUserContext.Provider value={{ authUser, setUser }}>
      {children}
    </AuthUserContext.Provider>
  );
};

export default AuthUserContext;
