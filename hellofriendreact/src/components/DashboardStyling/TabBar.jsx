
import React, { useState, Children, cloneElement } from 'react';
import TabBarBanner from './TabBarBanner';
import '/src/styles/OldStyles.css';
import useThemeMode from '/src/hooks/UseThemeMode';

const TabBar = ({ children }) => {
  const { themeMode } = useThemeMode();
  const [activeTab, setActiveTab] = useState(0);

  const handleTabClick = (index) => {
    setActiveTab(index);
  };

  const tabs = Children.toArray(children);

  return (
    <div className={`${themeMode === 'dark' ? 'dark-mode' : ''}`}>
      <div className="tab-bar-body">
        <TabBarBanner />

        <div className="tab-wrapper">
          <div className="tab-bar-box">
            {tabs.map((tab, index) =>
              cloneElement(tab, {
                key: index,
                active: index === activeTab,
                onClick: () => handleTabClick(index),
              })
            )}
            <div
              className="line"
              style={{
                width: `${100 / tabs.length}%`,
                left: `${(activeTab * 100) / tabs.length}%`,
              }}
            ></div>
          </div>

          {tabs.map((tab, index) => (
            <div
              key={index}
              className={`tab-content ${activeTab === index ? 'active' : ''}`}
            >
              <div className="text-as-spacer">
                <p>" "</p>
                <p>" "</p>
                <p>" "</p>
                <p>" "</p>
                <p>" "</p>
                <p>" "</p>
                <p>" "</p>
              </div>
              {activeTab === index && tab.props.children}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default TabBar;