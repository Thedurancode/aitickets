/**
 * useVoiceCommands Hook
 *
 * Custom React hook for voice command integration with AI-Tickets MCP server.
 * Provides voice recognition, text-to-speech, and command execution.
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { useMCP } from './useMCP'; // Assumes you have an MCP context

// Web Speech API types (extend window)
declare global {
  interface Window {
    webkitSpeechRecognition: any;
    SpeechRecognition: any;
  }
}

export interface VoiceCommandResult {
  success: boolean;
  voice_response?: string;
  data?: any;
  error?: string;
}

export interface UseVoiceCommandsOptions {
  continuous?: boolean;        // Keep listening after command
  interimResults?: boolean;     // Show interim recognition results
  language?: string;            // Recognition language (default: 'en-US')
  voiceRate?: number;          // Speech rate (0.1-10, default: 1.0)
  voicePitch?: number;         // Speech pitch (0-2, default: 1.0)
  voiceName?: string;          // Voice name (system-dependent)
  autoSpeak?: boolean;         // Automatically speak responses
}

export function useVoiceCommands(options: UseVoiceCommandsOptions = {}) {
  const {
    continuous = false,
    interimResults = false,
    language = 'en-US',
    voiceRate = 1.0,
    voicePitch = 1.0,
    voiceName,
    autoSpeak = true,
  } = options;

  const mcp = useMCP();
  const [listening, setListening] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [lastCommand, setLastCommand] = useState('');
  const [lastResponse, setLastResponse] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [supported, setSupported] = useState(false);

  const recognitionRef = useRef<any>(null);
  const utteranceQueueRef = useRef<string[]>([]);
  const isSpeakingRef = useRef(false);

  // Check browser support
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const speechSynthesis = window.speechSynthesis;

    if (SpeechRecognition && speechSynthesis) {
      setSupported(true);
    } else {
      setSupported(false);
      setError('Voice features not supported in this browser');
    }
  }, []);

  /**
   * Text-to-Speech function
   */
  const speak = useCallback((text: string, priority: 'normal' | 'high' = 'normal') => {
    if (!window.speechSynthesis) {
      console.error('Speech synthesis not supported');
      return;
    }

    // Stop current speech if high priority
    if (priority === 'high' && isSpeakingRef.current) {
      window.speechSynthesis.cancel();
      utteranceQueueRef.current = [];
    }

    // Add to queue
    utteranceQueueRef.current.push(text);

    // Process queue if not currently speaking
    if (!isSpeakingRef.current) {
      processUtteranceQueue();
    }
  }, []);

  /**
   * Process utterance queue
   */
  const processUtteranceQueue = useCallback(() => {
    if (utteranceQueueRef.current.length === 0) {
      isSpeakingRef.current = false;
      setSpeaking(false);
      return;
    }

    isSpeakingRef.current = true;
    setSpeaking(true);

    const text = utteranceQueueRef.current.shift()!;
    const utterance = new SpeechSynthesisUtterance(text);

    utterance.rate = voiceRate;
    utterance.pitch = voicePitch;

    // Set voice if specified
    if (voiceName) {
      const voices = window.speechSynthesis.getVoices();
      const voice = voices.find(v => v.name === voiceName);
      if (voice) utterance.voice = voice;
    }

    utterance.onend = () => {
      processUtteranceQueue();
    };

    utterance.onerror = (event) => {
      console.error('Speech synthesis error:', event);
      isSpeakingRef.current = false;
      setSpeaking(false);
      utteranceQueueRef.current = [];
    };

    window.speechSynthesis.speak(utterance);
  }, [voiceRate, voicePitch, voiceName]);

  /**
   * Stop speaking
   */
  const stopSpeaking = useCallback(() => {
    window.speechSynthesis.cancel();
    utteranceQueueRef.current = [];
    isSpeakingRef.current = false;
    setSpeaking(false);
  }, []);

  /**
   * Execute voice command against MCP server
   */
  const executeCommand = useCallback(async (command: string): Promise<VoiceCommandResult> => {
    setLastCommand(command);
    setError(null);

    const lower = command.toLowerCase();

    try {
      let result: any;

      // Alert commands
      if (lower.includes('show alerts') || lower.includes('what alerts')) {
        result = await mcp.callTool('show_alerts', {});
      } else if (lower.match(/any (critical|urgent) alerts/)) {
        result = await mcp.callTool('check_critical_alerts', {});
      } else if (lower.match(/dismiss alert (\d+)/)) {
        const match = lower.match(/dismiss alert (\d+)/);
        const alertId = parseInt(match![1]);
        result = await mcp.callTool('dismiss_alert', { alert_id: alertId });
      } else if (lower.includes('clear') && lower.includes('alerts')) {
        result = await mcp.callTool('clear_alerts', {});
      }

      // Campaign commands
      else if (lower.includes('show campaigns')) {
        result = await mcp.callTool('show_campaigns', {});
      } else if (lower.match(/campaign (\d+) (performance|stats|how did)/)) {
        const match = lower.match(/campaign (\d+)/);
        const campaignId = parseInt(match![1]);
        result = await mcp.callTool('campaign_performance', { campaign_id: campaignId });
      } else if (lower.includes('top campaigns')) {
        result = await mcp.callTool('top_campaigns', {});
      }

      // Dashboard commands
      else if (lower.match(/^(status|how are we doing)/)) {
        result = await mcp.callTool('quick_status', {});
      } else if (lower.match(/(today('s)? revenue|how much.*today)/)) {
        result = await mcp.callTool('todays_revenue', {});
      } else if (lower.includes('revenue today')) {
        result = await mcp.callTool('revenue_today', {});
      } else if (lower.includes('top events')) {
        result = await mcp.callTool('top_events', {});
      }

      // Unknown command
      else {
        const errorMsg = "I didn't understand that command. Try saying 'show alerts', 'status', or 'top campaigns'.";
        setError(errorMsg);
        if (autoSpeak) {
          speak(errorMsg);
        }
        return {
          success: false,
          error: errorMsg,
        };
      }

      // Parse MCP response
      const parsedResult = typeof result === 'string' ? JSON.parse(result) : result;

      const voiceResponse = parsedResult.voice_response || 'Command executed successfully.';
      setLastResponse(voiceResponse);

      // Automatically speak response if enabled
      if (autoSpeak) {
        speak(voiceResponse);
      }

      return {
        success: true,
        voice_response: voiceResponse,
        data: parsedResult,
      };

    } catch (err: any) {
      const errorMsg = `Error executing command: ${err.message}`;
      setError(errorMsg);
      if (autoSpeak) {
        speak('Sorry, there was an error processing your command.');
      }
      return {
        success: false,
        error: errorMsg,
      };
    }
  }, [mcp, autoSpeak, speak]);

  /**
   * Start listening for voice commands
   */
  const startListening = useCallback(() => {
    if (!supported) {
      setError('Voice recognition not supported');
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!recognitionRef.current) {
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = continuous;
      recognitionRef.current.interimResults = interimResults;
      recognitionRef.current.lang = language;

      recognitionRef.current.onstart = () => {
        setListening(true);
        setError(null);
        setTranscript('');
      };

      recognitionRef.current.onresult = (event: any) => {
        const results = event.results;
        const lastResult = results[results.length - 1];

        if (lastResult.isFinal) {
          const command = lastResult[0].transcript;
          setTranscript(command);
          executeCommand(command);
        } else {
          // Interim result
          setTranscript(lastResult[0].transcript);
        }
      };

      recognitionRef.current.onerror = (event: any) => {
        console.error('Speech recognition error:', event.error);
        setError(`Recognition error: ${event.error}`);
        setListening(false);
      };

      recognitionRef.current.onend = () => {
        setListening(false);
        if (continuous && recognitionRef.current) {
          // Restart if continuous mode
          setTimeout(() => {
            if (recognitionRef.current) {
              recognitionRef.current.start();
            }
          }, 100);
        }
      };
    }

    try {
      recognitionRef.current.start();
    } catch (err) {
      console.error('Failed to start recognition:', err);
      setError('Failed to start voice recognition');
    }
  }, [supported, continuous, interimResults, language, executeCommand]);

  /**
   * Stop listening
   */
  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      setListening(false);
    }
  }, []);

  /**
   * Toggle listening
   */
  const toggleListening = useCallback(() => {
    if (listening) {
      stopListening();
    } else {
      startListening();
    }
  }, [listening, startListening, stopListening]);

  /**
   * Get available voices
   */
  const getVoices = useCallback(() => {
    if (!window.speechSynthesis) return [];
    return window.speechSynthesis.getVoices();
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      stopSpeaking();
    };
  }, [stopSpeaking]);

  return {
    // State
    listening,
    speaking,
    transcript,
    lastCommand,
    lastResponse,
    error,
    supported,

    // Methods
    startListening,
    stopListening,
    toggleListening,
    executeCommand,
    speak,
    stopSpeaking,
    getVoices,
  };
}
