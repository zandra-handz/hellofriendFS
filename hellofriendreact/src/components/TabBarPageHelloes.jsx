import React, { useEffect, useState } from 'react';
import api from '../api';
import CardUneditable from './DashboardStyling/CardUneditable';
import useSelectedFriend from '../hooks/UseSelectedFriend';
import useThemeMode from '../hooks/UseThemeMode';
import TabSpinner from './DashboardStyling/TabSpinner';

const TabBarPageHelloes = () => {
  const { themeMode } = useThemeMode();
  const [helloesData, setHelloesData] = useState([]);
  const { selectedFriend } = useSelectedFriend();

  useEffect(() => {
    const fetchData = async () => {
      try {
        if (selectedFriend) {
          const response = await api.get(`/friends/${selectedFriend.id}/helloes/`);
          setHelloesData(response.data);
        }
      } catch (error) {
        console.error('Error fetching data:', error);
      }
    };

    fetchData();
  }, [selectedFriend]);

  return (
    <div>
      <h1> </h1>
      {helloesData.length > 0 ? (
        helloesData.map((hello) => (
          <div key={hello.id}>
            <CardUneditable title={`${hello.past_date_in_words} @ ${hello.location_name || 'Unknown'}`}>
              <p> 
              </p>
              <ul>
                {Object.entries(hello.thought_capsules_shared).map(([capsuleId, capsuleData]) => (
                  <li key={capsuleId}>
                    {capsuleData.typed_category || 'Unspecified'}
                  </li>
                ))}
              </ul>
            </CardUneditable>
          </div>
        ))
      ) : (
        <TabSpinner />
      )}
    </div>
  );
};

export default TabBarPageHelloes;
