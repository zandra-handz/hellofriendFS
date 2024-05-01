import React from 'react';

const MessageError = ({ sentenceObject }) => {
  return <div className="message error">{sentenceObject.message}</div>;
};

export default MessageError;
