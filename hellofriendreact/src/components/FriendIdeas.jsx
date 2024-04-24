import React, { useEffect, useState } from 'react';
import api from '../api';
import CardExpand from './DashboardStyling/CardExpand';
import ButtonExpandAll from './DashboardStyling/ButtonExpandAll';
import ItemCapsule from './DashboardStyling/ItemCapsule';
import TabSpinner from './DashboardStyling/TabSpinner';
import useAuthUser from '../hooks/UseAuthUser';
import useSelectedFriend from '../hooks/UseSelectedFriend';
import useThemeMode from '/src/hooks/UseThemeMode';

const FriendIdeas = () => {
  const { themeMode } = useThemeMode();
  const [categoryData, setCategoryData] = useState({});
  const [expandedCategories, setExpandedCategories] = useState({});
  const { authUser } = useAuthUser();
  const { selectedFriend } = useSelectedFriend();

  useEffect(() => {
    const fetchData = async () => {
      try {
        if (selectedFriend) {
          // Fetch category data
          const categoryDataResponse = await api.get(`/friends/${selectedFriend.id}/thoughtcapsules/by-category/`);
          setCategoryData(categoryDataResponse.data);
          // Initialize expandedCategories state
          const initialExpandedCategories = {};
          Object.keys(categoryDataResponse.data).forEach(category => {
            initialExpandedCategories[category] = false;
          });
          setExpandedCategories(initialExpandedCategories);
        }
      } catch (error) {
        console.error('Error fetching data:', error);
      }
    };

    fetchData();
  }, [authUser, selectedFriend]);

  const toggleCategory = (category) => {
    setExpandedCategories((prev) => ({
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
      
      {Object.keys(categoryData).length > 0 ? (
        Object.entries(categoryData).map(([category, capsules]) => (
          <div key={category}>
            <CardExpand
              title={`Category: ${category}`}
              expanded={expandedCategories[category]}
              onExpandButtonClick={() => toggleCategory(category)}
            >
              {expandedCategories[category] && capsules.map((capsule) => (
                <ItemCapsule key={capsule.id} capsule={capsule.capsule} />
              ))}
            </CardExpand>
          </div>
        ))
      ) : (
        <p><TabSpinner/></p>
      )}
    </div>
  );
};

export default FriendIdeas;
