import React, { useEffect, useState } from 'react';
import api from '../api';
import useSelectedFriend from '../hooks/UseSelectedFriend'; 
import useThemeMode from '../hooks/UseThemeMode';
import Card from './DashboardStyling/Card';
import MainNextHelloButton from './DashboardStyling/MainNextHelloButton';
import useFriendList from '../hooks/UseFriendList'; // Import useFriendList hook

const NextHelloes = () => {
    const { themeMode } = useThemeMode();
    const [data, setData] = useState(null);
    const { selectedFriend, setFriend } = useSelectedFriend();
    const { friendList } = useFriendList(); // Get friendList from the hook

    useEffect(() => {
        const fetchData = async () => {
            try {
                const response = await api.get('/friends/upcoming/');
                setData(response.data);
            } catch (error) {
                console.error('Error fetching data:', error);
            }
        };

        fetchData();
    }, [friendList.length]); // Trigger effect when friendList length changes

    const handleFriendClick = (friendId) => {
        setFriend(friendId);
    };

    return (
        <div>
            <Card title='Next Helloes'>
                {data && (
                    <div>
                        {data.map((item) => (
                            <div key={item.id}>
                                <ul>
                                    <li>
                                        {/* Use the MainNextHelloButton component here */}
                                        <MainNextHelloButton
                                            friendName={item.friend_name}
                                            futureDate={item.future_date_in_words}
                                            friendObject={item.friend}
                                        />
                                    </li>
                                </ul>
                            </div>
                        ))}
                    </div>
                )}
            </Card>
        </div>
    );
};

export default React.memo(NextHelloes);
