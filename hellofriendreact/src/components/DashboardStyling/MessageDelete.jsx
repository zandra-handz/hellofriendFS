import React from 'react';

const MessageDelete = ({ sentenceObject }) => {
  return <div className="message deleted">{sentenceObject.message}</div>;
};

export default MessageDelete;