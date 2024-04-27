import { useContext } from 'react';
import UpcomingHelloesContext from '../context/UpcomingHelloesProvider';

const useUpcomingHelloes = () => {
    const context = useContext(UpcomingHelloesContext);

    if (!context) {
        throw new Error('useUpcomingHelloes must be used within an UpcomingHelloesProvider');
    }

    return context;
};


export default useUpcomingHelloes;


