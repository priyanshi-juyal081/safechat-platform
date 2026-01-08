import { useState, useEffect, useRef, useCallback } from 'react';

export const useSpeechRecognition = (streamId, userId, isStreaming) => {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [warnings, setWarnings] = useState(0);
  const [isTimedOut, setIsTimedOut] = useState(false);
  const [timeoutRemaining, setTimeoutRemaining] = useState(0);
  const [streamStopped, setStreamStopped] = useState(false);
  
  const recognitionRef = useRef(null);
  const speechWsRef = useRef(null);
  const timeoutIntervalRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const lastSentTranscriptRef = useRef('');
  const processingRef = useRef(false);
  const lastRestartRef = useRef(0);
  const resumeOnWsOpenRef = useRef(false);
  const isStreamingRef = useRef(isStreaming);

  // Keep track of isStreaming in a ref so we can access it in cleanup
  useEffect(() => {
    isStreamingRef.current = isStreaming;
  }, [isStreaming]);

  // Throttle function to prevent sending too many requests
  const throttledSend = useCallback((ws, transcript) => {
    // Don't send if already processing or if it's the same as last sent
    if (processingRef.current || transcript === lastSentTranscriptRef.current) {
      return;
    }

    // Don't send very short transcripts
    if (transcript.length < 3) {
      return;
    }

    processingRef.current = true;
    lastSentTranscriptRef.current = transcript;

    console.log('🎤 SENDING TO BACKEND:', transcript);

    ws.send(JSON.stringify({
      type: 'speech_transcript',
      transcript: transcript,
      user_id: userId,
      stream_id: streamId,
      timestamp: new Date().toISOString()
    }));

    // Reset processing flag after a short delay (reduced for faster detection)
    setTimeout(() => {
      processingRef.current = false;
    }, 500); // Wait 500ms before allowing next send
  }, [userId, streamId]);

  const startTimeoutCountdown = useCallback((duration) => {
    let remaining = duration;
    
    if (timeoutIntervalRef.current) {
      clearInterval(timeoutIntervalRef.current);
    }
    
    console.log(`⏰ Starting timeout countdown: ${duration} seconds`);
    
    timeoutIntervalRef.current = setInterval(() => {
      remaining -= 1;
      setTimeoutRemaining(remaining);
      
      if (remaining <= 0) {
        clearInterval(timeoutIntervalRef.current);
        setIsTimedOut(false);
        setTimeoutRemaining(0);
        console.log('✅ Timeout ended, resuming speech recognition');
        
        // Resume speech recognition only if still streaming
        if (recognitionRef.current && isStreamingRef.current) {
          try {
            recognitionRef.current.start();
            setIsListening(true);
          } catch (e) {
            console.warn('Could not restart recognition:', e);
          }
        }
      }
    }, 1000);
  }, []);

  // Main effect for speech recognition
  useEffect(() => {
    // If not streaming, clean up and return early
    if (!isStreaming || !streamId || !userId) {
      console.log('❌ Not starting speech recognition: streaming ended or missing requirements');
      
      // Clean up if recognition is active
      if (recognitionRef.current) {
        try {
          console.log('🧹 Stopping speech recognition (stream ended)');
          recognitionRef.current.stop();
          setIsListening(false);
        } catch (e) {
          console.warn('Error stopping recognition:', e);
        }
      }
      
      if (speechWsRef.current) {
        speechWsRef.current.close();
      }
      
      return;
    }

    console.log(`🎙️ Initializing speech recognition for stream ${streamId}, user ${userId}`);

    // Initialize Web Speech API
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
      console.error('❌ Speech recognition not supported in this browser');
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = false; // Only get final results for better performance
    recognition.maxAlternatives = 1; // Only get best match
    recognition.lang = 'en-US';

    // Connect to speech moderation WebSocket
    const connectSpeechWebSocket = () => {
      console.log(`🔌 Connecting to speech WebSocket: ws://localhost:8000/ws/speech/${streamId}/${userId}/`);
      const ws = new WebSocket(`ws://localhost:8000/ws/speech/${streamId}/${userId}/`);
      
      ws.onopen = () => {
        console.log('✅ Speech moderation WebSocket connected');
        // If we were waiting to resume recognition until WS opened, do that now
        if (resumeOnWsOpenRef.current && recognitionRef.current && isStreamingRef.current && !isTimedOut && !streamStopped) {
          try {
            recognitionRef.current.start();
            setIsListening(true);
            resumeOnWsOpenRef.current = false;
            console.log('✅ Resumed recognition after WS open');
          } catch (e) {
            console.warn('Could not resume recognition on WS open:', e);
          }
        }
      };
      
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('📨 Speech moderation message:', data.type, data);

        if (data.type === 'speech_warning') {
          console.log(`⚠️ WARNING ${data.warning_number}/3 received`);
          setWarnings(data.warning_number);
          
          // Show alert with warning details
          alert(data.message || `Warning ${data.warning_number}/3: Your speech contains inappropriate content`);
          
        } else if (data.type === 'speech_timeout') {
          console.log(`🔇 TIMEOUT received: ${data.timeout_duration} seconds`);
          setWarnings(data.warning_number);
          setIsTimedOut(true);
          setTimeoutRemaining(data.timeout_duration);
          
          alert(data.message || `You have been muted for ${data.timeout_duration} seconds`);
          
          // Start countdown
          startTimeoutCountdown(data.timeout_duration);
          
          // Stop recognition during timeout
          if (recognitionRef.current) {
            try {
              recognitionRef.current.stop();
              setIsListening(false);
            } catch (e) {
              console.warn('Error stopping recognition:', e);
            }
          }
          
        } else if (data.type === 'stream_stopped') {
          console.log('🚫 STREAM STOPPED due to violations');
          setStreamStopped(true);
          alert(data.message || 'Your stream has been terminated due to repeated violations');
          
          // Stop recognition immediately
          if (recognitionRef.current) {
            try {
              recognitionRef.current.stop();
              setIsListening(false);
            } catch (e) {
              console.warn('Error stopping recognition:', e);
            }
          }
          
        } else if (data.type === 'speech_toxic') {
          console.log('🚨 TOXIC SPEECH DETECTED!');
          console.log('   Transcript:', data.transcript);
          console.log('   Details:', data.details);
          console.log('   Warning #:', data.warning_number);
          
        } else if (data.type === 'speech_clean') {
          console.log('✅ Speech is clean:', data.transcript);
          setTranscript(data.transcript);
          
        } else if (data.type === 'timeout_active') {
          console.log('⏸️ User is timed out, cannot speak');
        } else if (data.type === 'timeout_expired') {
          console.log('✅ Timeout expired notification:', data);
          // If this expiry is for this user+stream, clear timeout UI and resume recognition
          if (String(data.user_id) === String(userId) && String(data.stream_id) === String(streamId)) {
            setIsTimedOut(false);
            setTimeoutRemaining(0);
            console.log('✅ Cleared timeout state; attempting to resume recognition');

            // Clear any existing countdown
            if (timeoutIntervalRef.current) {
              clearInterval(timeoutIntervalRef.current);
            }

            // Resume recognition if possible
            if (recognitionRef.current && isStreamingRef.current && !streamStopped) {
              try {
                recognitionRef.current.start();
                setIsListening(true);
              } catch (e) {
                console.warn('Could not restart recognition after timeout expiry:', e);
              }
            }
          }
        }
      };
      
      ws.onerror = (error) => {
        console.error('❌ Speech WebSocket error:', error);
      };
      
      ws.onclose = () => {
        console.log('🔌 Speech WebSocket disconnected');
        // Stop listening when WS disconnects to avoid lost transcripts
        setIsListening(false);

        // Only attempt to reconnect if still streaming and not stopped
        if (isStreamingRef.current && !streamStopped) {
          console.log('🔄 Will attempt to reconnect in 3 seconds...');
          reconnectTimeoutRef.current = setTimeout(() => {
            if (isStreamingRef.current) {
              connectSpeechWebSocket();
            }
          }, 3000);
        }
      };
      
      speechWsRef.current = ws;
    };

    recognition.onresult = (event) => {
      // Only process if still streaming
      if (!isStreamingRef.current) {
        console.log('⚠️ Ignoring transcript: stream has ended');
        return;
      }

      // Only process final results for better performance
      for (let i = event.resultIndex; i < event.results.length; i++) {
        if (event.results[i].isFinal) {
          const transcript = event.results[i][0].transcript.trim();
          
          console.log('🎤 FINAL TRANSCRIPT:', transcript);
          
          if (transcript && speechWsRef.current && 
              speechWsRef.current.readyState === WebSocket.OPEN && 
              !isTimedOut && !streamStopped) {
            // Use throttled send
            throttledSend(speechWsRef.current, transcript);
          }
        }
      }
    };

    recognition.onerror = (event) => {
      console.error('❌ Speech recognition error:', event.error);
      
      if (event.error === 'no-speech') {
        // Silently restart for no-speech errors
        console.log('🔄 No speech detected, restarting...');
        if (isStreamingRef.current && !isTimedOut && !streamStopped) {
          try {
            recognition.start();
          } catch (e) {
            // Ignore if already started
          }
        }
      } else if (event.error === 'aborted') {
        // Ignore aborted errors
        console.log('⚠️ Recognition aborted');
      } else {
        console.error('Speech recognition error:', event.error);
      }
    };

    recognition.onend = () => {
      console.log('🎙️ Recognition ended');
      
      // Auto-restart only if still streaming and not timed out
      const now = Date.now();
      const RESTART_COOLDOWN = 800; // ms
      if (isStreamingRef.current && !isTimedOut && !streamStopped) {
        if (now - lastRestartRef.current < RESTART_COOLDOWN) {
          console.log('⏱️ Restart cooldown active, skipping restart');
          setIsListening(false);
          return;
        }

        lastRestartRef.current = now;
        console.log('🔄 Restarting recognition...');
        // small delay to avoid immediate start/stop race conditions
        setTimeout(() => {
          if (isStreamingRef.current && !isTimedOut && !streamStopped) {
            // Only start if WS is open to avoid lost transcripts
            if (speechWsRef.current && speechWsRef.current.readyState === WebSocket.OPEN) {
              try {
                recognition.start();
                console.log('🎙️ Recognition restarted');
              } catch (e) {
                console.warn('Could not restart recognition:', e);
              }
            } else {
              // Wait for WS to open then resume
              resumeOnWsOpenRef.current = true;
              console.log('⏳ Delaying recognition restart until WS opens');
            }
          }
        }, 200);
      } else {
        console.log('❌ Not restarting recognition (streaming ended or timed out)');
        setIsListening(false);
      }
    };

    recognition.onstart = () => {
      console.log('🎙️ Recognition started');
      setIsListening(true);
    };

    recognitionRef.current = recognition;
    connectSpeechWebSocket();

    // Start recognition
    try {
      recognition.start();
      console.log('✅ Speech recognition initialized and started');
    } catch (e) {
      console.warn('Could not start recognition:', e);
    }

    // Cleanup function
    return () => {
      console.log('🧹 Cleaning up speech recognition');
      
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
          setIsListening(false);
        } catch (e) {
          // Ignore errors on cleanup
        }
      }
      
      if (speechWsRef.current) {
        speechWsRef.current.close();
      }
      
      if (timeoutIntervalRef.current) {
        clearInterval(timeoutIntervalRef.current);
      }
      
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [streamId, userId, isStreaming, isTimedOut, streamStopped, throttledSend, startTimeoutCountdown]);

  return {
    isListening,
    transcript,
    warnings,
    isTimedOut,
    timeoutRemaining,
    streamStopped
  };
};