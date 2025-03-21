import React, { useState } from 'react';
import './Chatbot.css';

const Chatbot = () => {
  const [query, setQuery] = useState('');
  const [response, setResponse] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch('http://localhost:5000/create-chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query }),
      });
      const data = await res.json();
      setResponse(data.response);
    } catch (error) {
      console.error('Error fetching response:', error);
      setResponse('Error fetching response');
    }
  };

  return (
    <div className="chatbot-container">
      <div className="chatbot-response">
        <h3>Chatbot Response:</h3>
        <p>{response}</p>
      </div>
      <form onSubmit={handleSubmit} className="chatbot-form">
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Enter your query..."
          rows="4"
          className="chatbot-textarea"
        />
        <button type="submit" className="chatbot-submit-button">
          Submit
        </button>
      </form>
    </div>
  );
};

export default Chatbot;