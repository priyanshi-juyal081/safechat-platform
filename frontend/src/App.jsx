import React, { useState, useEffect, useRef } from 'react';
import { Video, Send, AlertTriangle, Ban, Eye, Users, MessageSquare, Radio, Wifi, WifiOff } from 'lucide-react';

const SocialModerationPlatform = () => {
  const [user, setUser] = useState(null);
  const [activeTab, setActiveTab] = useState('chat');
  const [messages, setMessages] = useState([]);
  const [liveStreams, setLiveStreams] = useState([]);
  const [currentStream, setCurrentStream] = useState(null);
  const [messageInput, setMessageInput] = useState('');
  const [username, setUsername] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamTitle, setStreamTitle] = useState('');
  const [warnings, setWarnings] = useState({});
  const [restrictedUsers, setRestrictedUsers] = useState(new Set());
  const [wsConnected, setWsConnected] = useState(false);
  
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const chatContainerRef = useRef(null);
  const wsRef = useRef(null);
  const streamWsRef = useRef(null);

  // WebSocket connection for global chat
  useEffect(() => {
    if (!user) return;

    const connectWebSocket = () => {
      const ws = new WebSocket('ws://localhost:8000/ws/chat/');
      
      ws.onopen = () => {
        console.log('WebSocket connected');
        setWsConnected(true);
      };
      
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('WebSocket message:', data);

        if (data.type === 'message_history') {
          setMessages(prev => mergeMessages(prev, data.messages, null));
        } else if (data.type === 'new_message') {
          const msg = data.message;
          const serverMsg = {
            id: msg.id,
            userId: msg.user_id,
            username: msg.username,
            text: msg.text,
            timestamp: new Date(msg.timestamp),
            streamId: msg.stream_id || null,
            flagged: msg.is_flagged
          };

          setMessages(prev => {
            let replaced = false;
            const next = prev.map(p => {
              if (!replaced && String(p.id).startsWith('local-') && p.username === serverMsg.username && p.text === serverMsg.text && Math.abs(new Date(p.timestamp) - serverMsg.timestamp) < 5000) {
                replaced = true;
                return serverMsg;
              }
              return p;
            });

            if (!replaced) {
              return [...next, serverMsg];
            }
            return next;
          });
        } else if (data.type === 'warning') {
          setWarnings(prev => ({ ...prev, [user.id]: data.warning_count }));
          alert(data.message);
        } else if (data.type === 'restriction') {
          setRestrictedUsers(prev => new Set([...prev, user.id]));
          alert(data.message);
        }
      };
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setWsConnected(false);
      };
      
      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setWsConnected(false);
        // Reconnect after 3 seconds
        setTimeout(connectWebSocket, 3000);
      };
      
      wsRef.current = ws;
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [user]);

  // WebSocket for stream chat
  useEffect(() => {
    if (!user || !currentStream) return;

    const connectStreamWebSocket = () => {
      const ws = new WebSocket(`ws://localhost:8000/ws/chat/${currentStream.id}/`);
      
      ws.onopen = () => {
        console.log('Stream WebSocket connected');
      };
      
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === 'message_history') {
          setMessages(prev => mergeMessages(prev, data.messages, currentStream.id));
        } else if (data.type === 'new_message') {
          const msg = data.message;
          const serverMsg = {
            id: msg.id,
            userId: msg.user_id,
            username: msg.username,
            text: msg.text,
            timestamp: new Date(msg.timestamp),
            streamId: currentStream.id,
            flagged: msg.is_flagged
          };

          setMessages(prev => {
            let replaced = false;
            const next = prev.map(p => {
              if (!replaced && String(p.id).startsWith('local-') && p.username === serverMsg.username && p.text === serverMsg.text && Math.abs(new Date(p.timestamp) - serverMsg.timestamp) < 5000) {
                replaced = true;
                return serverMsg;
              }
              return p;
            });

            if (!replaced) {
              return [...next, serverMsg];
            }
            return next;
          });
        } else if (data.type === 'warning') {
          setWarnings(prev => ({ ...prev, [user.id]: data.warning_count }));
          alert(data.message);
        } else if (data.type === 'restriction') {
          setRestrictedUsers(prev => new Set([...prev, user.id]));
          alert(data.message);
        }
      };
      
      ws.onerror = (error) => {
        console.error('Stream WebSocket error:', error);
      };
      
      ws.onclose = () => {
        console.log('Stream WebSocket disconnected');
      };
      
      streamWsRef.current = ws;
    };

    connectStreamWebSocket();

    return () => {
      if (streamWsRef.current) {
        streamWsRef.current.close();
      }
    };
  }, [user, currentStream]);

  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages]);

  // Ensure the active video element always has the current MediaStream attached.
  useEffect(() => {
    const attachStreamToVideo = async () => {
      if (isStreaming && streamRef.current && videoRef.current) {
        try {
          if (videoRef.current.srcObject !== streamRef.current) {
            videoRef.current.srcObject = streamRef.current;
          }
          await videoRef.current.play();
        } catch (err) {
          console.warn('Could not autoplay attached stream:', err);
        }
      }
    };

    attachStreamToVideo();
  }, [isStreaming, currentStream, activeTab]);

  const handleLogin = () => {
    if (username.trim()) {
      setUser({
        id: Date.now(),
        username: username.trim(),
        joinedAt: new Date()
      });
    }
  };

  const handleSendMessage = () => {
    if (!messageInput.trim() || !user) return;

    if (restrictedUsers.has(user.id)) {
      alert('You are restricted from chatting due to violations.');
      return;
    }

    // Choose WebSocket and stream context based on active tab to avoid mixing chats
    const ws = activeTab === 'chat' ? wsRef.current : streamWsRef.current;
    const targetStreamId = activeTab === 'chat' ? null : (currentStream ? currentStream.id : null);

    if (ws && ws.readyState === WebSocket.OPEN) {
      const msgText = messageInput.trim();

      ws.send(JSON.stringify({
        type: 'chat_message',
        username: user.username,
        user_id: user.id,
        message: msgText
      }));

      const localMsg = {
        id: `local-${Date.now()}`,
        userId: user.id,
        username: user.username,
        text: msgText,
        timestamp: new Date(),
        streamId: targetStreamId,
        flagged: false
      };

      setMessages(prev => [...prev, localMsg]);

      setMessageInput('');
    } else {
      alert('Not connected to chat server. Please wait...');
    }
  };

  const handleStartStream = async () => {
    if (!streamTitle.trim()) {
      alert('Please enter a stream title');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: true,
        audio: true
      });

      if (videoRef.current) {
        try {
          videoRef.current.srcObject = stream;
          // Some browsers require an explicit play() call even with autoplay/muted
          await videoRef.current.play();
        } catch (err) {
          console.warn('Could not autoplay video element:', err);
        }
      }

      streamRef.current = stream;
      
      const newStream = {
        id: Date.now(),
        streamerId: user.id,
        streamerName: user.username,
        title: streamTitle.trim(),
        viewers: 0,
        startedAt: new Date(),
        isLive: true
      };

      setLiveStreams(prev => [...prev, newStream]);
      setCurrentStream(newStream);
      setIsStreaming(true);
      setActiveTab('live');
    } catch (err) {
      console.error('Error accessing camera:', err);
      alert('Could not access camera. Please grant camera permissions.');
    }
  };

  // Merge server history with local messages for a specific chat context (global or a stream)
  // targetStreamId: null for global chat, or a stream id for stream chat
  const mergeMessages = (prevMessages, serverMessages, targetStreamId = null) => {
    const incoming = serverMessages.map(msg => ({
      id: msg.id,
      userId: msg.user_id,
      username: msg.username,
      text: msg.text,
      timestamp: new Date(msg.timestamp),
      streamId: msg.stream_id === undefined ? null : msg.stream_id,
      flagged: msg.is_flagged
    })).filter(m => m.streamId === targetStreamId);

    const incomingIds = new Set(incoming.map(m => m.id));

    const keptLocal = prevMessages.filter(pm => {
      // Always keep messages for other streams
      if (pm.streamId !== targetStreamId) return true;

      // For local optimistic messages in this stream, remove if server confirmed
      if (String(pm.id).startsWith('local-')) {
        const match = incoming.find(im => im.username === pm.username && im.text === pm.text && Math.abs(im.timestamp - new Date(pm.timestamp)) < 5000);
        return !match;
      }

      // For server-sourced prev messages in this stream, keep only if not present in incoming (avoid duplicates)
      return !incomingIds.has(pm.id);
    });

    const merged = [...prevMessages.filter(pm => pm.streamId !== targetStreamId), ...incoming, ...keptLocal.filter(pm => pm.streamId === targetStreamId)];
    merged.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
    return merged;
  };

  const handleStopStream = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }

    if (currentStream) {
      setLiveStreams(prev => 
        prev.map(s => s.id === currentStream.id ? { ...s, isLive: false } : s)
      );
    }

    setIsStreaming(false);
    setCurrentStream(null);
    setStreamTitle('');
    if (videoRef.current) {
      try {
        videoRef.current.srcObject = null;
      } catch (e) {}
    }
  };

  const handleJoinStream = (stream) => {
    setCurrentStream(stream);
    setActiveTab('live');
    setLiveStreams(prev =>
      prev.map(s => s.id === stream.id ? { ...s, viewers: s.viewers + 1 } : s)
    );
  };

  const handleLeaveStream = () => {
    if (currentStream) {
      setLiveStreams(prev =>
        prev.map(s => s.id === currentStream.id ? { ...s, viewers: Math.max(0, s.viewers - 1) } : s)
      );
    }
    setCurrentStream(null);
  };

  const handleModeratorWarn = (messageId, userId) => {
    setMessages(prev =>
      prev.map(msg => msg.id === messageId ? { ...msg, flagged: true } : msg)
    );
    
    const userWarnings = warnings[userId] || 0;
    setWarnings(prev => ({ ...prev, [userId]: userWarnings + 1 }));
    
    if (userWarnings + 1 >= 3) {
      setRestrictedUsers(prev => new Set([...prev, userId]));
    }
  };

  const handleModeratorRestrict = (userId) => {
    setRestrictedUsers(prev => new Set([...prev, userId]));
  };

  const getFilteredMessages = () => {
    if (activeTab === 'chat') {
      return messages.filter(msg => msg.streamId === null);
    }

    if (activeTab === 'live' && currentStream) {
      return messages.filter(msg => msg.streamId === currentStream.id);
    }

    // default to global chat messages
    return messages.filter(msg => msg.streamId === null);
  };

  const handleKeyPress = (e, handler) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handler();
    }
  };

  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-900 via-blue-900 to-indigo-900 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-2xl p-8 w-full max-w-md">
          <div className="text-center mb-8">
            <div className="inline-block p-3 bg-purple-100 rounded-full mb-4">
              <Users className="w-12 h-12 text-purple-600" />
            </div>
            <h1 className="text-3xl font-bold text-gray-800 mb-2">SafeChat</h1>
            <p className="text-gray-600">AI-Powered Real-Time Social Platform</p>
          </div>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Choose a username
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                onKeyPress={(e) => handleKeyPress(e, handleLogin)}
                placeholder="Enter username"
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>
            <button
              onClick={handleLogin}
              className="w-full bg-purple-600 text-white py-3 rounded-lg font-semibold hover:bg-purple-700 transition"
            >
              Join Platform
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-white shadow-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-purple-100 rounded-lg">
              <Users className="w-6 h-6 text-purple-600" />
            </div>
            <h1 className="text-2xl font-bold text-gray-800">SafeChat</h1>
            <div className="flex items-center space-x-1">
              {wsConnected ? (
                <div className="flex items-center space-x-1 text-green-600 text-xs">
                  <Wifi className="w-4 h-4" />
                  <span>Live</span>
                </div>
              ) : (
                <div className="flex items-center space-x-1 text-red-600 text-xs">
                  <WifiOff className="w-4 h-4" />
                  <span>Connecting...</span>
                </div>
              )}
            </div>
          </div>
          
          <div className="flex items-center space-x-4">
            <span className="text-sm text-gray-600">
              Welcome, <span className="font-semibold">{user.username}</span>
            </span>
            {warnings[user.id] > 0 && (
              <div className="flex items-center space-x-1 text-yellow-600 bg-yellow-50 px-3 py-1 rounded-full">
                <AlertTriangle className="w-4 h-4" />
                <span className="text-sm font-medium">{warnings[user.id]}/3 Warnings</span>
              </div>
            )}
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto p-4 flex gap-4">
        <div className="w-64 space-y-4">
          <div className="bg-white rounded-lg shadow-md p-4">
            <h3 className="font-semibold text-gray-800 mb-3">Navigation</h3>
            <div className="space-y-2">
              <button
                onClick={() => setActiveTab('chat')}
                className={`w-full flex items-center space-x-2 px-3 py-2 rounded-lg transition ${
                  activeTab === 'chat' ? 'bg-purple-100 text-purple-700' : 'hover:bg-gray-100'
                }`}
              >
                <MessageSquare className="w-4 h-4" />
                <span>Global Chat</span>
              </button>
              <button
                onClick={() => setActiveTab('streams')}
                className={`w-full flex items-center space-x-2 px-3 py-2 rounded-lg transition ${
                  activeTab === 'streams' ? 'bg-purple-100 text-purple-700' : 'hover:bg-gray-100'
                }`}
              >
                <Video className="w-4 h-4" />
                <span>Live Streams</span>
              </button>
              <button
                onClick={() => setActiveTab('golive')}
                className={`w-full flex items-center space-x-2 px-3 py-2 rounded-lg transition ${
                  activeTab === 'golive' ? 'bg-purple-100 text-purple-700' : 'hover:bg-gray-100'
                }`}
              >
                <Radio className="w-4 h-4" />
                <span>Go Live</span>
              </button>
            </div>
          </div>

          {liveStreams.filter(s => s.isLive).length > 0 && (
            <div className="bg-white rounded-lg shadow-md p-4">
              <h3 className="font-semibold text-gray-800 mb-3 flex items-center">
                <span className="w-2 h-2 bg-red-500 rounded-full mr-2 animate-pulse"></span>
                Live Now
              </h3>
              <div className="space-y-2">
                {liveStreams.filter(s => s.isLive).map(stream => (
                  <button
                    key={stream.id}
                    onClick={() => handleJoinStream(stream)}
                    className="w-full text-left p-2 hover:bg-gray-50 rounded-lg transition"
                  >
                    <div className="text-sm font-medium text-gray-800 truncate">
                      {stream.title}
                    </div>
                    <div className="text-xs text-gray-500 flex items-center justify-between mt-1">
                      <span>{stream.streamerName}</span>
                      <span className="flex items-center">
                        <Eye className="w-3 h-3 mr-1" />
                        {stream.viewers}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="flex-1">
          {activeTab === 'chat' && (
            <div className="bg-white rounded-lg shadow-md h-[calc(100vh-150px)] flex flex-col">
              <div className="p-4 border-b">
                <h2 className="text-xl font-bold text-gray-800">Global Chat</h2>
                <p className="text-sm text-gray-600">Real-time chat with AI moderation</p>
              </div>

              <div ref={chatContainerRef} className="flex-1 overflow-y-auto p-4 space-y-3">
                {getFilteredMessages().map(msg => (
                  <div key={msg.id} className={`p-3 rounded-lg ${msg.flagged ? 'bg-red-50 border border-red-200' : 'bg-gray-50'}`}>
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-2">
                          <span className="font-semibold text-gray-800">{msg.username}</span>
                          <span className="text-xs text-gray-500">
                            {msg.timestamp.toLocaleTimeString()}
                          </span>
                          {msg.flagged && (
                            <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full">
                              Flagged
                            </span>
                          )}
                        </div>
                        <p className="text-gray-700 mt-1">{msg.text}</p>
                      </div>
                      {msg.userId !== user.id && !msg.flagged && (
                        <div className="flex space-x-1 ml-2">
                          <button
                            onClick={() => handleModeratorWarn(msg.id, msg.userId)}
                            className="p-1 hover:bg-yellow-100 rounded"
                            title="Warn user"
                          >
                            <AlertTriangle className="w-4 h-4 text-yellow-600" />
                          </button>
                          <button
                            onClick={() => handleModeratorRestrict(msg.userId)}
                            className="p-1 hover:bg-red-100 rounded"
                            title="Restrict user"
                          >
                            <Ban className="w-4 h-4 text-red-600" />
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              <div className="p-4 border-t flex space-x-2">
                <input
                  type="text"
                  value={messageInput}
                  onChange={(e) => setMessageInput(e.target.value)}
                  onKeyPress={(e) => handleKeyPress(e, handleSendMessage)}
                  placeholder={restrictedUsers.has(user.id) ? "You are restricted" : "Type a message..."}
                  disabled={restrictedUsers.has(user.id) || !wsConnected}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent disabled:bg-gray-100"
                />
                <button
                  onClick={handleSendMessage}
                  disabled={restrictedUsers.has(user.id) || !wsConnected}
                  className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition disabled:bg-gray-400 flex items-center space-x-2"
                >
                  <Send className="w-4 h-4" />
                  <span>Send</span>
                </button>
              </div>
            </div>
          )}

          {activeTab === 'golive' && (
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-bold text-gray-800 mb-6">Start Live Stream</h2>
              
              {!isStreaming ? (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Stream Title
                    </label>
                    <input
                      type="text"
                      value={streamTitle}
                      onChange={(e) => setStreamTitle(e.target.value)}
                      placeholder="What are you streaming?"
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                    />
                  </div>
                  
                  <button
                    onClick={handleStartStream}
                    className="w-full bg-red-600 text-white py-3 rounded-lg font-semibold hover:bg-red-700 transition flex items-center justify-center space-x-2"
                  >
                    <Radio className="w-5 h-5" />
                    <span>Go Live</span>
                  </button>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="bg-black rounded-lg overflow-hidden aspect-video">
                    <video
                      ref={videoRef}
                      autoPlay
                      muted
                      playsInline
                      className="w-full h-full object-cover"
                    />
                  </div>
                  
                  <div className="flex items-center justify-between p-4 bg-red-50 rounded-lg">
                    <div className="flex items-center space-x-2">
                      <span className="w-3 h-3 bg-red-500 rounded-full animate-pulse"></span>
                      <span className="font-semibold text-red-700">LIVE</span>
                      <span className="text-gray-600">|</span>
                      <span className="text-gray-700">{currentStream?.viewers || 0} viewers</span>
                    </div>
                    <button
                      onClick={handleStopStream}
                      className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition"
                    >
                      End Stream
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'live' && currentStream && (
            <div className="bg-white rounded-lg shadow-md overflow-hidden">
              <div className="bg-black aspect-video flex items-center justify-center">
                {currentStream.streamerId === user.id ? (
                  <video
                    ref={videoRef}
                    autoPlay
                    muted
                    playsInline
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="text-white text-center">
                    <Video className="w-16 h-16 mx-auto mb-4 opacity-50" />
                    <p className="text-lg">Watching: {currentStream.streamerName}</p>
                    <p className="text-sm opacity-75 mt-2">{currentStream.title}</p>
                  </div>
                )}
              </div>

              <div className="p-4 border-b flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-gray-800">{currentStream.title}</h3>
                  <p className="text-sm text-gray-600">{currentStream.streamerName}</p>
                </div>
                <div className="flex items-center space-x-4">
                  <div className="flex items-center space-x-2 text-gray-600">
                    <Eye className="w-5 h-5" />
                    <span className="font-semibold">{currentStream.viewers}</span>
                  </div>
                  {currentStream.streamerId !== user.id && (
                    <button
                      onClick={handleLeaveStream}
                      className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition"
                    >
                      Leave
                    </button>
                  )}
                </div>
              </div>

              <div className="h-96 overflow-y-auto p-4 space-y-3">
                {getFilteredMessages().map(msg => (
                  <div key={msg.id} className={`p-3 rounded-lg ${msg.flagged ? 'bg-red-50 border border-red-200' : 'bg-gray-50'}`}>
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-2">
                          <span className="font-semibold text-gray-800">{msg.username}</span>
                          <span className="text-xs text-gray-500">
                            {msg.timestamp.toLocaleTimeString()}
                          </span>
                          {msg.flagged && (
                            <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full">
                              Flagged
                            </span>
                          )}
                        </div>
                        <p className="text-gray-700 mt-1">{msg.text}</p>
                      </div>
                      {msg.userId !== user.id && !msg.flagged && (
                        <div className="flex space-x-1 ml-2">
                          <button
                            onClick={() => handleModeratorWarn(msg.id, msg.userId)}
                            className="p-1 hover:bg-yellow-100 rounded"
                            title="Warn user"
                          >
                            <AlertTriangle className="w-4 h-4 text-yellow-600" />
                          </button>
                          <button
                            onClick={() => handleModeratorRestrict(msg.userId)}
                            className="p-1 hover:bg-red-100 rounded"
                            title="Restrict user"
                          >
                            <Ban className="w-4 h-4 text-red-600" />
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              <div className="p-4 border-t flex space-x-2">
                <input
                  type="text"
                  value={messageInput}
                  onChange={(e) => setMessageInput(e.target.value)}
                  onKeyPress={(e) => handleKeyPress(e, handleSendMessage)}
                  placeholder={restrictedUsers.has(user.id) ? "You are restricted" : "Comment on stream..."}
                  disabled={restrictedUsers.has(user.id)}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent disabled:bg-gray-100"
                />
                <button
                  onClick={handleSendMessage}
                  disabled={restrictedUsers.has(user.id)}
                  className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition disabled:bg-gray-400"
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {activeTab === 'streams' && (
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-bold text-gray-800 mb-6">Live Streams</h2>
              
              {liveStreams.filter(s => s.isLive).length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <Video className="w-16 h-16 mx-auto mb-4 opacity-50" />
                  <p>No live streams at the moment</p>
                  <p className="text-sm mt-2">Be the first to go live!</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {liveStreams.filter(s => s.isLive).map(stream => (
                    <div
                      key={stream.id}
                      className="border border-gray-200 rounded-lg overflow-hidden hover:shadow-lg transition cursor-pointer"
                      onClick={() => handleJoinStream(stream)}
                    >
                      <div className="bg-gradient-to-br from-purple-500 to-blue-500 aspect-video flex items-center justify-center relative">
                        <Video className="w-12 h-12 text-white opacity-75" />
                        <div className="absolute top-3 left-3 bg-red-600 text-white px-2 py-1 rounded text-xs font-semibold flex items-center space-x-1">
                          <span className="w-2 h-2 bg-white rounded-full animate-pulse"></span>
                          <span>LIVE</span>
                        </div>
                      </div>
                      <div className="p-4">
                        <h3 className="font-semibold text-gray-800 mb-1">{stream.title}</h3>
                        <p className="text-sm text-gray-600 mb-2">{stream.streamerName}</p>
                        <div className="flex items-center text-sm text-gray-500">
                          <Eye className="w-4 h-4 mr-1" />
                          <span>{stream.viewers} viewers</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default SocialModerationPlatform;