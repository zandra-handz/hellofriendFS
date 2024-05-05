import React, { useEffect } from 'react';
import api from '../api';
import Card from './DashboardStyling/Card';
import GridOneOrTwoColsAnyRows from './DashboardStyling/GridOneOrTwoColsAnyRows';
import MainNextHelloButton from './DashboardStyling/MainNextHelloButton';
import useUpcomingHelloes from '../hooks/UseUpcomingHelloes';

const NextHelloes = () => {
    const { upcomingHelloes } = useUpcomingHelloes();

    return (
        <div>
            <Card title='Say hi!'>
                <GridOneOrTwoColsAnyRows>
                    {upcomingHelloes && upcomingHelloes.map((item) => (
                        <MainNextHelloButton
                            friendName={item.friend_name}
                            futureDate={item.future_date_in_words}
                            friendObject={item.friend}
                            key={item.id}
                        />
                    ))}
                </GridOneOrTwoColsAnyRows>
            </Card>
        </div>
    );
};

export default React.memo(NextHelloes);
