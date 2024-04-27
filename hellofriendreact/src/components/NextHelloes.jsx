import React, { useEffect } from 'react';
import api from '../api';
import Card from './DashboardStyling/Card';
import MainNextHelloButton from './DashboardStyling/MainNextHelloButton';
import useUpcomingHelloes from '../hooks/UseUpcomingHelloes';

const NextHelloes = () => {
    const { upcomingHelloes } = useUpcomingHelloes();

    return (
        <div>
            <Card title='Next Helloes'>
                {upcomingHelloes && (
                    <div>
                        {upcomingHelloes.map((item) => (
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
