/**
 * VoiceUI Component
 *
 * Complete voice interface with transcript history, controls, and settings.
 * Displays conversation between user and AI-Tickets system.
 */

import React, { useState, useEffect, useRef } from 'react';
import { useVoiceCommands } from '../../hooks/useVoiceCommands';
import './VoiceUI.css';

export interface VoiceUIProps {
  className?: string;
  showHistory?: boolean;
  showSettings?: boolean;
}

interface ConversationEntry {
  type: 'user' | 'system';
  text: string;
  timestamp: Date;
}

export const VoiceUI: React.FC<VoiceUIProps> = ({
  className = '',
  showHistory = true,
  showSettings = false,
}) => {
  const [conversation, setConversation] = useState<ConversationEntry[]>([]);
  const [voiceRate, setVoiceRate] = useState(1.0);
  const [voicePitch, setVoicePitch] = useState(1.0);
  const [continuous, setContinuous] = useState(false);
  const conversationEndRef = useRef<HTMLDivElement>(null);

  const {
    listening,
    speaking,
    transcript,
    lastCommand,
    lastResponse,
    error,
    supported,
    startListening,
    stopListening,
    speak,
    stopSpeaking,
    getVoices,
  } = useVoiceCommands({
    continuous,
    voiceRate,
    voicePitch,
  });

  // Add to conversation when command/response changes
  useEffect(() => {
    if (lastCommand && lastResponse) {
      setConversation(prev => [
        ...prev.filter(entry => entry.text !== lastCommand && entry.text !== lastResponse),
        {
          type: 'user',
          text: lastCommand,
          timestamp: new Date(),
        },
        {
          type: 'system',
          text: lastResponse,
          timestamp: new Date(),
        },
      ]);
    }
  }, [lastCommand, lastResponse]);

  // Auto-scroll to bottom
  useEffect(() => {
    conversationEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversation]);

  // Get available voices for selection
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);
  useEffect(() => {
    const loadVoices = () => {
      const availableVoices = getVoices();
      setVoices(availableVoices);
    };

    loadVoices();
    if (window.speechSynthesis) {
      window.speechSynthesis.onvoiceschanged = loadVoices;
    }
  }, [getVoices]);

  if (!supported) {
    return (
      <div className={`voice-ui voice-ui--unsupported ${className}`}>
        <div className="voice-ui-error">
          <h3>Voice Commands Not Supported</h3>
          <p>
            Your browser doesn't support voice commands. Please use a modern browser like Chrome,
            Edge, or Safari.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={`voice-ui ${className}`}>
      {/* Header */}
      <div className="voice-ui-header">
        <h2>AI-Tickets Voice Assistant</h2>
        <div className="voice-ui-status">
          {listening && <span className="status-badge status-badge--listening">Listening...</span>}
          {speaking && <span className="status-badge status-badge--speaking">Speaking...</span>}
          {!listening && !speaking && (
            <span className="status-badge status-badge--ready">Ready</span>
          )}
        </div>
      </div>

      {/* Main voice button and transcript */}
      <div className="voice-ui-main">
        <button
          className={`voice-ui-mic ${listening ? 'voice-ui-mic--active' : ''}`}
          onClick={listening ? stopListening : startListening}
          disabled={speaking}
        >
          {listening ? (
            <>
              <MicActiveIcon />
              <span>Stop</span>
            </>
          ) : (
            <>
              <MicIcon />
              <span>Speak</span>
            </>
          )}
        </button>

        {listening && transcript && (
          <div className="voice-ui-transcript">
            <div className="voice-ui-transcript-label">You said:</div>
            <div className="voice-ui-transcript-text">{transcript}</div>
          </div>
        )}

        {speaking && lastResponse && (
          <div className="voice-ui-speaking">
            <div className="voice-ui-speaking-label">AI-Tickets:</div>
            <div className="voice-ui-speaking-text">{lastResponse}</div>
            <button className="voice-ui-stop-button" onClick={stopSpeaking}>
              Stop Speaking
            </button>
          </div>
        )}

        {error && (
          <div className="voice-ui-error-message">
            <ErrorIcon />
            {error}
          </div>
        )}
      </div>

      {/* Conversation history */}
      {showHistory && conversation.length > 0 && (
        <div className="voice-ui-history">
          <h3>Conversation History</h3>
          <div className="voice-ui-history-list">
            {conversation.map((entry, index) => (
              <div
                key={index}
                className={`voice-ui-history-item voice-ui-history-item--${entry.type}`}
              >
                <div className="voice-ui-history-avatar">
                  {entry.type === 'user' ? <UserIcon /> : <BotIcon />}
                </div>
                <div className="voice-ui-history-content">
                  <div className="voice-ui-history-text">{entry.text}</div>
                  <div className="voice-ui-history-time">
                    {entry.timestamp.toLocaleTimeString()}
                  </div>
                </div>
              </div>
            ))}
            <div ref={conversationEndRef} />
          </div>
          <button
            className="voice-ui-clear-button"
            onClick={() => setConversation([])}
          >
            Clear History
          </button>
        </div>
      )}

      {/* Settings */}
      {showSettings && (
        <div className="voice-ui-settings">
          <h3>Voice Settings</h3>

          <div className="voice-ui-setting">
            <label>
              <input
                type="checkbox"
                checked={continuous}
                onChange={(e) => setContinuous(e.target.checked)}
              />
              Continuous listening
            </label>
          </div>

          <div className="voice-ui-setting">
            <label>
              Speech Rate: {voiceRate.toFixed(1)}x
              <input
                type="range"
                min="0.5"
                max="2"
                step="0.1"
                value={voiceRate}
                onChange={(e) => setVoiceRate(parseFloat(e.target.value))}
              />
            </label>
          </div>

          <div className="voice-ui-setting">
            <label>
              Speech Pitch: {voicePitch.toFixed(1)}
              <input
                type="range"
                min="0.5"
                max="2"
                step="0.1"
                value={voicePitch}
                onChange={(e) => setVoicePitch(parseFloat(e.target.value))}
              />
            </label>
          </div>
        </div>
      )}

      {/* Quick commands help */}
      <div className="voice-ui-help">
        <details>
          <summary>Voice Commands</summary>
          <div className="voice-ui-commands">
            <div className="voice-ui-command-group">
              <h4>Alerts</h4>
              <ul>
                <li>"Show alerts"</li>
                <li>"Any critical alerts?"</li>
                <li>"Dismiss alert 5"</li>
                <li>"Clear alerts"</li>
              </ul>
            </div>
            <div className="voice-ui-command-group">
              <h4>Dashboard</h4>
              <ul>
                <li>"Status"</li>
                <li>"Today's revenue"</li>
                <li>"Top events"</li>
              </ul>
            </div>
            <div className="voice-ui-command-group">
              <h4>Campaigns</h4>
              <ul>
                <li>"Show campaigns"</li>
                <li>"Top campaigns"</li>
                <li>"Campaign 5 performance"</li>
              </ul>
            </div>
          </div>
        </details>
      </div>
    </div>
  );
};

// Icon components
const MicIcon = () => (
  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
    <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
    <line x1="12" y1="19" x2="12" y2="23" />
    <line x1="8" y1="23" x2="16" y2="23" />
  </svg>
);

const MicActiveIcon = () => (
  <svg width="32" height="32" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" strokeWidth="2">
    <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
    <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
    <line x1="12" y1="19" x2="12" y2="23" />
    <line x1="8" y1="23" x2="16" y2="23" />
  </svg>
);

const UserIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
    <circle cx="12" cy="7" r="4" />
  </svg>
);

const BotIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <rect x="3" y="11" width="18" height="10" rx="2" />
    <circle cx="12" cy="5" r="2" />
    <path d="M12 7v4" />
    <line x1="8" y1="16" x2="8" y2="16" />
    <line x1="16" y1="16" x2="16" y2="16" />
  </svg>
);

const ErrorIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="12" cy="12" r="10" />
    <line x1="12" y1="8" x2="12" y2="12" />
    <line x1="12" y1="16" x2="12.01" y2="16" />
  </svg>
);
