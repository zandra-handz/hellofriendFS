import React from 'react'; 
import '/src/styles/OldStyles.css';

const FriendDashHeader = ({ friendDaysSince, friendNextHello }) => {
  return ( 
    <div className="gradient-background"> 
        <div className="card-container">
        <div className="half-width-card">
            {friendDaysSince}  
        </div>
        <div className="half-width-card">
            {friendNextHello}
        </div>
        </div> 
    </div>
  );
};

export default FriendDashHeader;

