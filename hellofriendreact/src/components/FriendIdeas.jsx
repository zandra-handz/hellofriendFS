import React, { useState, useEffect } from 'react';
import CardExpand from './DashboardStyling/CardExpand';
import ButtonExpandAll from './DashboardStyling/ButtonExpandAll';
import ItemCapsule from './DashboardStyling/ItemCapsule';
import TabSpinner from './DashboardStyling/TabSpinner';
import useSelectedFriend from '../hooks/UseSelectedFriend';
import useCapsuleList from '../hooks/UseCapsuleList'; 

const FriendIdeas = () => { 
  const [expandedCategories, setExpandedCategories] = useState({});
  const { selectedFriend } = useSelectedFriend();
  const { capsuleList } = useCapsuleList();

  useEffect(() => {
    if (capsuleList.length > 0) {
      // Initialize expandedCategories based on capsuleList
      const initialExpandedCategories = {};
      capsuleList.forEach(capsule => {
        if (!initialExpandedCategories[capsule.typedCategory]) {
          initialExpandedCategories[capsule.typedCategory] = false;
        }
      });
      setExpandedCategories(initialExpandedCategories);
    }
  }, [capsuleList]);

  const toggleCategory = (category) => {
    setExpandedCategories(prev => ({
      ...prev,
      [category]: !prev[category],
    }));
  };

  const expandAll = () => {
    const allExpanded = Object.keys(expandedCategories).every(category => expandedCategories[category]);
    const newExpandedCategories = {};
    Object.keys(expandedCategories).forEach(category => {
      newExpandedCategories[category] = !allExpanded;
    });
    setExpandedCategories(newExpandedCategories);
  };

  return (
    <div>
      <ButtonExpandAll onClick={expandAll} expandText="Expand all" collapseText="Close all" /> 
      
      {capsuleList.length > 0 ? (
        Object.entries(capsuleList.reduce((acc, capsule) => {
          if (!acc[capsule.typedCategory]) {
            acc[capsule.typedCategory] = [];
          }
          acc[capsule.typedCategory].push(capsule);
          return acc;
        }, {})).map(([category, capsules]) => (
          <div key={category}>
            <CardExpand
              title={`Category: ${category}`}
              expanded={expandedCategories[category]}
              onExpandButtonClick={() => toggleCategory(category)}
            >
              {expandedCategories[category] && capsules.map(capsule => (
                <ItemCapsule key={capsule.id} capsule={capsule.capsule} />
              ))}
            </CardExpand>
          </div>
        ))
      ) : (
        <p></p>
      )}
    </div>
  );
};

export default FriendIdeas;