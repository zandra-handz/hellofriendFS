import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../api';

const UpcomingHelloesContext = createContext({ upcomingHelloes: [], setUpcomingHelloes: () => {} });

export const UpcomingHelloesProvider = ({ children }) => {
    const [upcomingHelloes, setUpcomingHelloes] = useState([]);
    const [updateTrigger, setUpdateTrigger] = useState(false); // New state for update trigger
  
    useEffect(() => {
      const fetchData = async () => {
        try {
          const response = await api.get('/friends/upcoming/');
          const upcomingHelloesData = response.data;
          setUpcomingHelloes(upcomingHelloesData);
        } catch (error) {
          console.error('Error fetching upcoming helloes:', error);
        }
      };
  
      fetchData();
    }, [updateTrigger]); // Update trigger as dependency
  
    const contextValue = {
      upcomingHelloes,
      setUpcomingHelloes,
      updateTrigger, // Include update trigger in the context value
      setUpdateTrigger,
    };
  
    return (
      <UpcomingHelloesContext.Provider value={contextValue}>
        {children}
      </UpcomingHelloesContext.Provider>
    );
  };
  

export default UpcomingHelloesContext;
