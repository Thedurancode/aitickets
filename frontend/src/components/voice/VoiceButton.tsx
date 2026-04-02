/**
 * VoiceButton Component
 *
 * A microphone button that activates voice recognition.
 * Shows visual feedback for listening, speaking, and errors.
 */

import React from 'react';
import { useVoiceCommands } from '../../hooks/useVoiceCommands';
import './VoiceButton.css';

export interface VoiceButtonProps {
  continuous?: boolean;
  autoSpeak?: boolean;
  onCommandExecuted?: (result: any) => void;
  className?: string;
}

export const VoiceButton: React.FC<VoiceButtonProps> = ({
  continuous = false,
  autoSpeak = true,
  onCommandExecuted,
  className = '',
}) => {
  const {
    listening,
    speaking,
    transcript,
    lastResponse,
    error,
    supported,
    toggleListening,
  } = useVoiceCommands({ continuous, autoSpeak });

  const handleClick = () => {
    toggleListening();
  };

  if (!supported) {
    return (
      <div className={`voice-button-container ${className}`}>
        <button
          className="voice-button voice-button--unsupported"
          disabled
          title="Voice commands not supported in this browser"
        >
          <MicOffIcon />
        </button>
        <span className="voice-button-error">Voice not supported</span>
      </div>
    );
  }

  return (
    <div className={`voice-button-container ${className}`}>
      <button
        className={`voice-button ${listening ? 'voice-button--listening' : ''} ${
          speaking ? 'voice-button--speaking' : ''
        } ${error ? 'voice-button--error' : ''}`}
        onClick={handleClick}
        title={listening ? 'Stop listening' : 'Start voice command'}
      >
        {listening ? (
          <MicActiveIcon className="voice-button-icon voice-button-icon--pulse" />
        ) : speaking ? (
          <SpeakerIcon className="voice-button-icon voice-button-icon--pulse" />
        ) : (
          <MicIcon className="voice-button-icon" />
        )}
      </button>

      {/* Status text */}
      {listening && (
        <div className="voice-button-status voice-button-status--listening">
          {transcript || 'Listening...'}
        </div>
      )}

      {speaking && (
        <div className="voice-button-status voice-button-status--speaking">
          Speaking...
        </div>
      )}

      {error && (
        <div className="voice-button-status voice-button-status--error">
          {error}
        </div>
      )}

      {!listening && !speaking && lastResponse && (
        <div className="voice-button-status voice-button-status--response">
          {lastResponse}
        </div>
      )}
    </div>
  );
};

// Icon components (you can replace with your icon library)
const MicIcon = ({ className = '' }: { className?: string }) => (
  <svg
    className={className}
    width="24"
    height="24"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
    <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
    <line x1="12" y1="19" x2="12" y2="23" />
    <line x1="8" y1="23" x2="16" y2="23" />
  </svg>
);

const MicActiveIcon = ({ className = '' }: { className?: string }) => (
  <svg
    className={className}
    width="24"
    height="24"
    viewBox="0 0 24 24"
    fill="currentColor"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
    <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
    <line x1="12" y1="19" x2="12" y2="23" />
    <line x1="8" y1="23" x2="16" y2="23" />
    <circle cx="12" cy="12" r="2" fill="red" />
  </svg>
);

const MicOffIcon = ({ className = '' }: { className?: string }) => (
  <svg
    className={className}
    width="24"
    height="24"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <line x1="1" y1="1" x2="23" y2="23" />
    <path d="M9 9v3a3 3 0 0 0 5.12 2.12M15 9.34V4a3 3 0 0 0-5.94-.6" />
    <path d="M17 16.95A7 7 0 0 1 5 12v-2m14 0v2a7 7 0 0 1-.11 1.23" />
    <line x1="12" y1="19" x2="12" y2="23" />
    <line x1="8" y1="23" x2="16" y2="23" />
  </svg>
);

const SpeakerIcon = ({ className = '' }: { className?: string }) => (
  <svg
    className={className}
    width="24"
    height="24"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
    <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07" />
  </svg>
);
