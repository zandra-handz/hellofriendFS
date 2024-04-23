import { useContext } from "react";
import AuthUserContext from "../context/AuthUserProvider";

const useAuthUser = () => {
    const context = useContext(AuthUserContext);
  
    if (!context) {
      throw new Error('useAuthUser must be used within an AuthUserProvider');
    }
  
    return context;
};

export default useAuthUser;