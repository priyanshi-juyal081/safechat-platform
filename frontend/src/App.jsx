import React, { useState, useEffect, useRef } from 'react';
import { Video, Send, AlertTriangle, Ban, Eye, Users, MessageSquare, Radio, Wifi, WifiOff, Mic, MicOff, Heart, Clock, Trash2, Flag, } from 'lucide-react';
import { useSpeechRecognition } from './hooks/useSpeechRecognition';
import Login from "./login";
import {
  uploadImage,
  createPost,
  getPosts,
  likePost,
  unlikePost,
  addView,
  reportPost,
  deletePost
} from "./firebase";
import './App.css';

const ChatMessage = ({ msg, isCurrentUser, onWarn, onRestrict }) => {
  const bubbleColor = isCurrentUser
    ? 'glass-effect-light text-white ml-auto'
    : 'glass-effect text-purple-100 mr-auto';
  const tailClass = isCurrentUser ? 'bubble-tail-right' : 'bubble-tail-left';
  const pronouns = "HE/HIM"; // Static for aesthetic match

  return (
    <div className={`flex items-end space-x-3 mb-6 animate-fade-in ${isCurrentUser ? 'flex-row-reverse space-x-reverse' : 'flex-row'}`}>
      <div className={`flex-shrink-0 w-12 h-12 rounded-full overflow-hidden avatar-glow bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center text-white font-bold text-lg`}>
        {msg.username.charAt(0).toUpperCase()}
      </div>

      <div className="flex flex-col max-w-[80%]">
        <div className={`flex items-center space-x-2 mb-1 px-2 ${isCurrentUser ? 'justify-end' : 'justify-start'}`}>
          <span className="text-xs font-bold text-purple-200 tracking-wider uppercase">{msg.username}</span>
          <span className="text-[10px] text-purple-400 bg-purple-900/40 px-1.5 py-0.5 rounded border border-purple-500/30 font-medium tracking-tight">
            {pronouns}
          </span>
          {msg.flagged && (
            <span className="flex items-center text-[10px] bg-red-500/20 text-red-300 border border-red-500/40 px-2 py-0.5 rounded-full">
              <AlertTriangle className="w-3 h-3 mr-1" />
              FLAGGED
            </span>
          )}
        </div>

        <div className={`message-bubble ${bubbleColor} ${tailClass}`}>
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.text}</p>
          <div className="flex items-center justify-between mt-2 pt-1 border-t border-white/5">
            <span className="text-[10px] opacity-40">
              {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
            {!isCurrentUser && !msg.flagged && (
              <div className="flex space-x-1 ml-4 self-end">
                <button
                  onClick={() => onWarn(msg.id, msg.userId)}
                  className="p-1 hover:bg-white/10 rounded transition-colors"
                  title="Warn user"
                >
                  <AlertTriangle className="w-3.5 h-3.5 text-yellow-500" />
                </button>
                <button
                  onClick={() => onRestrict(msg.userId)}
                  className="p-1 hover:bg-white/10 rounded transition-colors"
                  title="Restrict user"
                >
                  <Ban className="w-3.5 h-3.5 text-red-500" />
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

const SocialModerationPlatform = () => {
  const [user, setUser] = useState(null);
  const [activeTab, setActiveTab] = useState('chat');
  const [messages, setMessages] = useState([]);
  const [liveStreams, setLiveStreams] = useState([]);
  const [currentStream, setCurrentStream] = useState(null);
  const [messageInput, setMessageInput] = useState('');
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

  // Post Section States
  const [posts, setPosts] = useState([]);
  const fileInputRef = useRef(null);
  const [newPostImage, setNewPostImage] = useState(null);
  const [newPostCaption, setNewPostCaption] = useState("");

  const [previewUrl, setPreviewUrl] = useState(null);
  const [selectedImage, setSelectedImage] = useState(null);
  const [reportingPost, setReportingPost] = useState(null);
  const [reportReason, setReportReason] = useState("");
  const [reportDescription, setReportDescription] = useState("");

  const {
    isListening,
    transcript,
    warnings: speechWarnings,
    isTimedOut,
    timeoutRemaining,
    streamStopped
  } = useSpeechRecognition(
    currentStream?.id,
    user?.id,
    isStreaming && currentStream?.streamerId === user?.id
  );

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
          // Remove the most recent optimistic local message from this user (it was blocked)
          setMessages(prev => {
            for (let i = prev.length - 1; i >= 0; i--) {
              const m = prev[i];
              if (String(m.id).startsWith('local-') && m.userId === user.id) {
                const next = [...prev.slice(0, i), ...prev.slice(i + 1)];
                return next;
              }
            }
            return prev;
          });
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
          setMessages(prev => {
            for (let i = prev.length - 1; i >= 0; i--) {
              const m = prev[i];
              if (String(m.id).startsWith('local-') && m.userId === user.id) {
                const next = [...prev.slice(0, i), ...prev.slice(i + 1)];
                return next;
              }
            }
            return prev;
          });
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

  // Real-time listener for posts
  useEffect(() => {
    const unsubscribe = getPosts(setPosts);
    return () => unsubscribe();
  }, []);

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
    // This is now handled by the Login component in login.jsx
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
      } catch (e) { }
    }
  };

  useEffect(() => {
    if (streamStopped) {
      alert('🚨 STREAM TERMINATED: Repeated speech violations detected. Your access has been revoked.');

      // Use the shared stop handler so the stream is marked not-live in the list
      try {
        handleStopStream();
      } catch (e) {
        console.warn('Error during handleStopStream', e);
      }

      // Ensure UI redirects back to global chat
      setActiveTab('chat');
    }
  }, [streamStopped]);

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

  const speechWarningCount = typeof speechWarnings === 'object' && speechWarnings !== null
    ? (speechWarnings[user?.id] || 0)
    : (speechWarnings || 0);

  const handleImageSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      setNewPostImage(file);
      setPreviewUrl(URL.createObjectURL(file));
    }
  };

  const handleCreatePost = async () => {
    console.log("📝 Create Post Request:", {
      caption: newPostCaption,
      hasImage: !!newPostImage
    });

    if (!newPostCaption && !newPostImage) return;

    try {
      let imageUrl = null;
      if (newPostImage) {
        console.log("📸 Starting photo upload...");
        imageUrl = await uploadImage(newPostImage);
        console.log("✨ Photo upload complete. URL:", imageUrl);
      }

      console.log("📡 Calling firebase.createPost...");
      await createPost(user.id, user.username, newPostCaption, imageUrl);

      console.log("✅ Post created successfully!");
      setNewPostImage(null);
      setNewPostCaption("");
      setPreviewUrl(null);
      alert("Post created successfully!");
    } catch (error) {
      console.error("💥 Error in handleCreatePost:", error);
      alert("Error creating post: " + (error.message || "Unknown error"));
    }
  };

  const handleLikePost = async (post) => {
    if (!user) return;
    try {
      if (post.is_liked) {
        await unlikePost(post.id, user.id);
      } else {
        await likePost(post.id, user.id);
      }
    } catch (error) {
      console.error("Error liking post:", error);
    }
  };

  const handleViewPost = async (postId, imageUrl) => {
    setSelectedImage(imageUrl);
    try {
      await addView(postId);
    } catch (e) {
      console.error("Error incrementing view", e);
    }
  };

  const handleDeletePost = async (postId, postUserId) => {
    console.log("🗑️ Delete Request:", {
      postId,
      postIdType: typeof postId,
      postUserId,
      postUserIdType: typeof postUserId,
      currentUserId: user?.id,
      currentUserIdType: typeof user?.id,
      match: String(user?.id) === String(postUserId)
    });

    if (!user || (String(user.id) !== String(postUserId))) {
      console.error("❌ Ownership Mismatch!", {
        current: user?.id,
        owner: postUserId
      });
      alert("You can only delete your own posts.");
      return;
    }

    if (!window.confirm("Are you sure you want to delete this post?")) {
      console.log("🚫 Deletion cancelled by user");
      return;
    }

    try {
      console.log("📡 Calling firebase.deletePost for ID:", postId);
      await deletePost(postId);
      console.log("✅ Deletion confirmed by Firebase");
      alert("Post deleted successfully!");
    } catch (error) {
      console.error("💥 Deletion error in component:", error);
      alert("Error deleting post: " + (error.message || "Unknown error"));
    }
  };

  const handleReportPost = async () => {
    if (!reportingPost || !reportReason) return;
    try {
      await reportPost(reportingPost.id, user.id, reportReason);
      alert("Post reported successfully. Thank you for making the community safe.");
      setReportingPost(null);
      setReportReason("");
      setReportDescription("");
    } catch (error) {
      console.error("Error reporting post:", error);
      alert("Error reporting post");
    }
  };

  if (!user) {
    return <Login onLogin={setUser} />;
  }

  return (
    <div className="global-bg-gradient min-h-screen">
      <header className="header-glass sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-purple-500/20 rounded-xl border border-purple-500/30">
              <Users className="w-6 h-6 text-purple-400" />
            </div>
            <h1 className="text-2xl font-black text-white tracking-tighter">SafeChat</h1>
            <div className="flex items-center space-x-1">
              {wsConnected ? (
                <div className="flex items-center space-x-1 text-green-600 text-xs">
                  <Wifi className="w-4 h-4" />
                  <span>Live</span>
                </div>
              ) : (
                <div className="flex items-center space-x-1 text-red-600 text-xs">
                  <WifiOff className="w-4 h-4" />
                  <span>Live Streams</span>
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center space-x-6">
            <span className="text-sm text-purple-100/60 font-medium">
              Welcome, <span className="text-white font-bold">{user.username}</span>
            </span>
            {/* UI Indicators for Speech Monitoring */}
            <div className="flex items-center space-x-4">
              {/* 1. Speech Monitoring Active: Green mic icon with pulse animation */}
              {isListening && !isTimedOut && !streamStopped && (
                <div className="flex items-center space-x-2 text-green-400 bg-green-500/10 px-3 py-1.5 rounded-full animate-pulse border border-green-500/20">
                  <Mic className="w-4 h-4" />
                  <span className="text-xs font-bold uppercase tracking-wider">Listening</span>
                </div>
              )}

              {/* 2. Timeout: Red mic-off icon with countdown timer */}
              {isTimedOut && (
                <div className="flex items-center space-x-2 text-red-400 bg-red-500/10 px-3 py-1.5 rounded-full border border-red-500/20 shadow-lg">
                  <MicOff className="w-4 h-4" />
                  <span className="text-xs font-bold uppercase tracking-wider">MUTED: {timeoutRemaining}s</span>
                </div>
              )}

              {/* 3. Warnings: Yellow warning badge showing "1/3", "2/3", "3/3" */}
              {speechWarningCount > 0 && !streamStopped && (
                <div className="flex items-center space-x-2 text-yellow-400 bg-yellow-500/10 px-3 py-1.5 rounded-full border border-yellow-500/20">
                  <AlertTriangle className="w-4 h-4" />
                  <span className="text-xs font-bold uppercase tracking-wider">Speech: {speechWarningCount}/3</span>
                </div>
              )}
            </div>

            {warnings[user.id] > 0 && (
              <div className="flex items-center space-x-2 text-orange-400 bg-orange-500/10 px-3 py-1.5 rounded-full border border-orange-500/20">
                <AlertTriangle className="w-4 h-4" />
                <span className="text-xs font-bold uppercase tracking-wider text-orange-400">{warnings[user.id]}/3 Warnings</span>
              </div>
            )}
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto p-6 flex gap-6 relative z-10">
        <div className="w-64 space-y-6">
          <div className="card-glass rounded-2xl p-4 overflow-hidden">
            <h3 className="text-xs font-black text-purple-300 uppercase tracking-[0.2em] mb-4 px-3 opacity-60">Engine</h3>
            <div className="space-y-1">
              <button
                onClick={() => setActiveTab('chat')}
                className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-all duration-300 ${activeTab === 'chat' ? 'nav-item-active' : 'text-purple-100/50 hover:text-white nav-item-hover'
                  }`}
              >
                <MessageSquare className="w-5 h-5" />
                <span className="font-bold text-sm">Global Chat</span>
              </button>
              <button
                onClick={() => setActiveTab('streams')}
                className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-all duration-300 ${activeTab === 'streams' ? 'nav-item-active' : 'text-purple-100/50 hover:text-white nav-item-hover'
                  }`}
              >
                <Video className="w-5 h-5" />
                <span className="font-bold text-sm">Live Streams</span>
              </button>
              <button
                onClick={() => setActiveTab('golive')}
                className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-all duration-300 ${activeTab === 'golive' ? 'nav-item-active' : 'text-purple-100/50 hover:text-white nav-item-hover'
                  }`}
              >
                <Radio className="w-5 h-5" />
                <span className="font-bold text-sm">Go Live</span>
              </button>
              <button
                onClick={() => setActiveTab('posts')}
                className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-all duration-300 ${activeTab === 'posts' ? 'nav-item-active' : 'text-purple-100/50 hover:text-white nav-item-hover'
                  }`}
              >
                <Heart className="w-5 h-5" />
                <span className="font-bold text-sm">Posts</span>
              </button>
            </div>
          </div>

          {liveStreams.filter(s => s.isLive).length > 0 && (
            <div className="card-glass rounded-2xl p-4">
              <h3 className="text-xs font-black text-red-400 uppercase tracking-[0.2em] mb-4 px-3 flex items-center">
                <span className="w-1.5 h-1.5 bg-red-500 rounded-full mr-2 animate-pulse"></span>
                Live Now
              </h3>
              <div className="space-y-2">
                {liveStreams.filter(s => s.isLive).map(stream => (
                  <button
                    key={stream.id}
                    onClick={() => handleJoinStream(stream)}
                    className="w-full text-left p-3 hover:bg-white/5 rounded-xl transition-all group"
                  >
                    <div className="text-sm font-bold text-white group-hover:text-purple-300 truncate">
                      {stream.title}
                    </div>
                    <div className="text-[10px] text-purple-200/40 flex items-center justify-between mt-1 font-bold uppercase tracking-widest">
                      <span>{stream.streamerName}</span>
                      <span className="flex items-center text-purple-300/60">
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
            <div className="chat-bg-gradient rounded-xl shadow-2xl h-[calc(100vh-150px)] flex flex-col border border-white/10 overflow-hidden">
              <div className="p-4 border-b border-white/10 glass-effect-light">
                <h2 className="text-xl font-bold text-white flex items-center space-x-2">
                  <div className="w-2 h-2 bg-purple-400 rounded-full animate-pulse" />
                  <span>Global Chat</span>
                </h2>
                <p className="text-sm text-purple-200/60">Encrypted and moderated real-time communication</p>
              </div>

              <div ref={chatContainerRef} className="flex-1 overflow-y-auto p-6 space-y-2 scrollbar-hide">
                {getFilteredMessages().map(msg => (
                  <ChatMessage
                    key={msg.id}
                    msg={msg}
                    isCurrentUser={msg.userId === user.id}
                    onWarn={handleModeratorWarn}
                    onRestrict={handleModeratorRestrict}
                  />
                ))}
              </div>

              <div className="p-4 border-t border-white/10 glass-effect-light flex space-x-2">
                <input
                  type="text"
                  value={messageInput}
                  onChange={(e) => setMessageInput(e.target.value)}
                  onKeyPress={(e) => handleKeyPress(e, handleSendMessage)}
                  placeholder={restrictedUsers.has(user.id) ? "Communication Disabled" : "Share your thoughts..."}
                  disabled={restrictedUsers.has(user.id) || !wsConnected}
                  className="flex-1 px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-purple-200/40 focus:ring-2 focus:ring-purple-500 focus:border-transparent disabled:bg-white/5 transition-all"
                />
                <button
                  onClick={handleSendMessage}
                  disabled={restrictedUsers.has(user.id) || !wsConnected}
                  className="px-6 py-2 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-xl hover:from-purple-700 hover:to-blue-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2 shadow-lg"
                >
                  <Send className="w-4 h-4" />
                  <span className="font-semibold">SEND</span>
                </button>
              </div>
            </div>
          )}

          {activeTab === 'golive' && (
            <div className="card-glass rounded-2xl p-8 border border-white/10 shadow-2xl overflow-hidden relative">
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-purple-500 to-blue-500"></div>
              <h2 className="text-2xl font-black text-white mb-8 tracking-tight flex items-center space-x-3">
                <div className="p-2 bg-red-500/10 rounded-lg border border-red-500/20">
                  <Radio className="w-6 h-6 text-red-400" />
                </div>
                <span>Start Live Stream</span>
              </h2>

              {!isStreaming ? (
                <div className="glass-effect-light rounded-xl p-6 border border-white/5 space-y-4">
                  <div>
                    <label className="block text-xs font-black text-purple-300 uppercase tracking-widest mb-2 px-1">
                      Stream Title
                    </label>
                    <input
                      type="text"
                      value={streamTitle}
                      onChange={(e) => setStreamTitle(e.target.value)}
                      placeholder="What are you streaming?"
                      className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/20 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
                    />
                  </div>

                  <button
                    onClick={handleStartStream}
                    className="w-full bg-gradient-to-r from-red-600 to-red-800 text-white py-4 rounded-xl font-black uppercase tracking-[0.2em] hover:from-red-700 hover:to-red-900 transition-all shadow-xl flex items-center justify-center space-x-3"
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
            <div className="chat-bg-gradient rounded-2xl shadow-2xl overflow-hidden border border-white/10 flex flex-col h-[calc(100vh-150px)]">
              <div className="bg-black aspect-video flex items-center justify-center relative group">
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
                    <Video className="w-16 h-16 mx-auto mb-4 text-purple-400 animate-pulse" />
                    <p className="text-lg font-black tracking-tight">Watching: {currentStream.streamerName}</p>
                    <p className="text-sm text-purple-200/40 mt-2">Transmitting from: {currentStream.streamerName}</p>
                  </div>
                )}
                <div className="absolute top-4 left-4 bg-red-600/80 backdrop-blur-md text-white px-3 py-1 rounded-full text-xs font-black tracking-widest flex items-center space-x-2">
                  <span className="w-2 h-2 bg-white rounded-full animate-ping"></span>
                  <span>LIVE</span>
                </div>
              </div>

              <div className="p-4 glass-effect-light border-b border-white/10 flex items-center justify-between">
                <div>
                  <h3 className="font-black text-white tracking-tight">{currentStream.title}</h3>
                  <p className="text-sm text-purple-200/60 font-bold uppercase tracking-widest">{currentStream.streamerName}</p>
                </div>
                <div className="flex items-center space-x-6">
                  <div className="flex items-center space-x-2 text-purple-300">
                    <Eye className="w-5 h-5" />
                    <span className="font-black">{currentStream.viewers}</span>
                  </div>
                  {currentStream.streamerId !== user.id && (
                    <button
                      onClick={handleLeaveStream}
                      className="px-4 py-2 bg-white/5 text-white rounded-xl hover:bg-white/10 border border-white/10 transition-all font-bold text-xs uppercase tracking-widest"
                    >
                      Leave
                    </button>
                  )}
                </div>
              </div>

              <div className="flex-1 overflow-y-auto p-4 space-y-2">
                {getFilteredMessages().map(msg => (
                  <ChatMessage
                    key={msg.id}
                    msg={msg}
                    isCurrentUser={msg.userId === user.id}
                    onWarn={handleModeratorWarn}
                    onRestrict={handleModeratorRestrict}
                  />
                ))}
              </div>

              <div className="p-4 glass-effect-light border-t border-white/10 flex space-x-2">
                <input
                  type="text"
                  value={messageInput}
                  onChange={(e) => setMessageInput(e.target.value)}
                  onKeyPress={(e) => handleKeyPress(e, handleSendMessage)}
                  placeholder={restrictedUsers.has(user.id) ? "Transmission Blocked" : "Comment on stream..."}
                  disabled={restrictedUsers.has(user.id)}
                  className="flex-1 px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-purple-200/40 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
                />
                <button
                  onClick={handleSendMessage}
                  disabled={restrictedUsers.has(user.id)}
                  className="px-4 py-2 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-xl hover:from-purple-700 hover:to-blue-700 shadow-lg disabled:opacity-50"
                >
                  <Send className="w-5 h-5" />
                </button>
              </div>
            </div>
          )}

          {activeTab === 'streams' && (
            <div className="card-glass rounded-2xl p-8 shadow-2xl min-h-[500px]">
              <h2 className="text-3xl font-black text-white mb-8 tracking-tighter flex items-center space-x-3">
                <div className="p-2 bg-blue-500/10 rounded-lg border border-blue-500/20">
                  <Video className="w-6 h-6 text-blue-400" />
                </div>
                <span>Live Streams</span>
              </h2>

              {liveStreams.filter(s => s.isLive).length === 0 ? (
                <div className="text-center py-20 bg-white/5 rounded-3xl border border-white/5">
                  <Video className="w-20 h-20 mx-auto mb-6 text-purple-500/20" />
                  <p className="text-xl font-bold text-purple-100/40">No live streams at the moment</p>
                  <p className="text-sm text-purple-200/20 mt-2 uppercase tracking-widest font-black">Be the first to go live!</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {liveStreams.filter(s => s.isLive).map(stream => (
                    <div
                      key={stream.id}
                      className="glass-effect rounded-2xl overflow-hidden hover:border-purple-500/50 transition-all cursor-pointer group shadow-xl"
                      onClick={() => handleJoinStream(stream)}
                    >
                      <div className="bg-gradient-to-br from-purple-900 to-black aspect-video flex items-center justify-center relative">
                        <Video className="w-16 h-16 text-purple-500/20 group-hover:text-purple-400/40 transition-colors" />
                        <div className="absolute top-4 left-4 bg-red-600 text-white px-3 py-1 rounded-full text-[10px] font-black flex items-center space-x-2 tracking-widest shadow-lg">
                          <span className="w-2 h-2 bg-white rounded-full animate-ping"></span>
                          <span>LIVE</span>
                        </div>
                        <div className="absolute bottom-4 right-4 bg-black/60 backdrop-blur-md px-3 py-1 rounded-lg text-[10px] text-white font-bold flex items-center space-x-1">
                          <Users className="w-3 h-3 text-purple-400" />
                          <span>{stream.viewers}</span>
                        </div>
                      </div>
                      <div className="p-6">
                        <h3 className="text-xl font-black text-white mb-2 group-hover:text-purple-300 transition-colors">{stream.title}</h3>
                        <div className="flex items-center space-x-3 mt-4">
                          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center text-white font-bold text-xs">
                            {stream.streamerName[0].toUpperCase()}
                          </div>
                          <div>
                            <p className="text-xs font-black uppercase tracking-widest text-purple-200/60">{stream.streamerName}</p>
                            <p className="text-[10px] text-purple-300/40 font-bold">TRANSMITTING SINCE {new Date(stream.startedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
          {activeTab === "posts" && (
            <div className="card-glass rounded-2xl p-8 shadow-2xl relative">
              <div className="mb-12 border-b border-white/10 pb-12">
                <h2 className="text-3xl font-black text-white tracking-tighter flex items-center space-x-3 mb-6">
                  <div className="p-2 bg-purple-500/10 rounded-lg border border-purple-500/20">
                    <Heart className="w-6 h-6 text-purple-400" />
                  </div>
                  <span>Sharing Moments</span>
                </h2>

                <div className="glass-effect-light rounded-2xl p-6 border border-white/5 shadow-inner">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-4">
                      <label className="block text-xs font-black text-purple-300 uppercase tracking-widest mb-2 px-1">Share a photo</label>
                      <div className="relative group">
                        <input
                          type="file"
                          accept="image/*"
                          onChange={handleImageSelect}
                          ref={fileInputRef}
                          className="hidden"
                          id="post-image-input"
                        />
                        <label
                          htmlFor="post-image-input"
                          className="flex items-center justify-center w-full aspect-square md:aspect-video rounded-xl border-2 border-dashed border-white/10 hover:border-purple-500/50 bg-white/5 hover:bg-white/10 transition-all cursor-pointer group overflow-hidden"
                        >
                          {previewUrl ? (
                            <img src={previewUrl} alt="Preview" className="w-full h-full object-cover" />
                          ) : (
                            <div className="text-center">
                              <Radio className="w-8 h-8 mx-auto mb-2 text-purple-400/40 group-hover:scale-110 transition-transform" />
                              <span className="text-xs font-bold text-white/40 uppercase tracking-widest">Select Image</span>
                            </div>
                          )}
                        </label>
                      </div>
                    </div>
                    <div className="flex flex-col">
                      <label className="block text-xs font-black text-purple-300 uppercase tracking-widest mb-2 px-1">Description</label>
                      <textarea
                        value={newPostCaption}
                        onChange={(e) => setNewPostCaption(e.target.value)}
                        placeholder="Add a caption..."
                        className="flex-1 w-full px-4 py-4 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/20 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all resize-none mb-4"
                      />
                      <button
                        onClick={handleCreatePost}
                        disabled={!newPostImage && !newPostCaption}
                        className="w-full bg-gradient-to-r from-purple-600 to-blue-600 text-white py-4 rounded-xl font-black uppercase tracking-[0.2em] hover:from-purple-700 hover:to-blue-700 transition-all shadow-xl disabled:opacity-20 flex items-center justify-center space-x-2"
                      >
                        <Send className="w-4 h-4" />
                        <span>Post</span>
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <div className="max-w-2xl mx-auto space-y-12 pb-20">
                {posts.map(post => (
                  <div key={post.id} className="glass-effect rounded-3xl overflow-hidden hover:border-white/20 transition-all group shadow-2xl scale-[0.98] hover:scale-100">
                    <div className="p-4 flex items-center justify-between border-b border-white/5 bg-white/5">
                      <div className="flex items-center space-x-3">
                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center font-black text-white shadow-lg overflow-hidden border border-white/20">
                          {post.username[0].toUpperCase()}
                        </div>
                        <div>
                          <p className="font-black text-white text-sm tracking-tight">{post.username}</p>
                          <p className="text-[10px] text-purple-200/40 font-bold uppercase tracking-widest">
                            {post.createdAt ? (post.createdAt.toDate ? post.createdAt.toDate() : new Date(post.createdAt)).toLocaleDateString() : 'REALTIME'}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        {(String(user.id) === String(post.user_id || post.userId)) && (
                          <button
                            onClick={() => handleDeletePost(post.id, post.user_id || post.userId)}
                            className="p-2 text-white/20 hover:text-red-400 transition-colors"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        )}
                        <button
                          onClick={() => setReportingPost(post)}
                          className="p-2 text-white/20 hover:text-yellow-400 transition-colors"
                        >
                          <Flag className="w-4 h-4" />
                        </button>
                      </div>
                    </div>

                    {post.is_rumour && (
                      <div className="bg-red-500/10 border-l-4 border-red-500 p-4 m-4 rounded-r-xl">
                        <div className="flex items-center">
                          <AlertTriangle className="h-5 w-5 text-red-500 mr-3" />
                          <p className="text-xs text-red-400 font-black uppercase tracking-widest">
                            Fact Check: Potential False Information
                          </p>
                        </div>
                        {post.rumor_reason && (
                          <p className="text-[11px] text-white/60 mt-2 ml-8 leading-relaxed italic">
                            "{post.rumor_reason}"
                          </p>
                        )}
                      </div>
                    )}

                    {post.image && (
                      <div className="relative group cursor-pointer overflow-hidden" onClick={() => handleViewPost(post.id, post.image)}>
                        <img src={post.image} alt="Post content" className="w-full object-cover max-h-[500px] transition-transform duration-700 group-hover:scale-105" />
                        <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end p-8">
                          <div className="flex items-center text-white space-x-2">
                            <Eye className="w-5 h-5 text-purple-400" />
                            <span className="font-bold">Full Resolution</span>
                          </div>
                        </div>
                      </div>
                    )}

                    <div className="p-6 space-y-4">
                      <div className="flex items-center space-x-6">
                        <button
                          onClick={() => handleLikePost(post)}
                          className={`flex items-center space-x-2 transition-all ${post.is_liked ? 'text-red-500 scale-110' : 'text-white/40 hover:text-red-400'}`}
                        >
                          <Heart className={`w-6 h-6 ${post.is_liked ? 'fill-current shadow-[0_0_15px_rgba(239,68,68,0.5)]' : ''}`} />
                          <span className="font-black text-lg">{post.likes_count}</span>
                        </button>
                        <div className="flex items-center space-x-2 text-white/20">
                          <Eye className="w-6 h-6" />
                          <span className="font-black text-lg">{post.views}</span>
                        </div>
                      </div>
                      <p className="text-purple-50 leading-relaxed text-sm">
                        <span className="font-black text-purple-300 mr-2">@{post.username}</span>
                        {post.caption}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
      {/* Image Modal */}
      {selectedImage && (
        <div
          className="fixed inset-0 z-[100] bg-black/95 backdrop-blur-2xl flex items-center justify-center p-4 animate-fade-in"
          onClick={() => setSelectedImage(null)}
        >
          <div className="relative max-w-5xl max-h-[90vh] w-full h-full flex items-center justify-center">
            <button
              onClick={() => setSelectedImage(null)}
              className="absolute -top-12 right-0 text-white/60 hover:text-white transition-all transform hover:rotate-90"
            >
              <div className="p-2 border border-white/20 rounded-full hover:bg-white/10">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </div>
            </button>
            <img
              src={selectedImage}
              alt="Full view"
              className="max-w-full max-h-full object-contain rounded-2xl shadow-[0_0_50px_rgba(0,0,0,0.5)] border border-white/5"
              onClick={(e) => e.stopPropagation()}
            />
          </div>
        </div>
      )}

      {/* Report Modal */}
      {reportingPost && (
        <div className="fixed inset-0 z-[100] bg-black/60 backdrop-blur-md flex items-center justify-center p-4 animate-fade-in">
          <div className="card-glass rounded-3xl shadow-2xl max-w-md w-full overflow-hidden border border-white/20">
            <div className="p-8">
              <div className="flex items-center justify-between mb-8">
                <h3 className="text-2xl font-black text-white tracking-tight flex items-center space-x-2">
                  <div className="p-2 bg-red-500/10 rounded-lg">
                    <Flag className="w-5 h-5 text-red-500" />
                  </div>
                  <span>Report Post</span>
                </h3>
                <button
                  onClick={() => setReportingPost(null)}
                  className="text-white/20 hover:text-white transition-colors"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <div className="space-y-6">
                <div>
                  <label className="block text-xs font-black text-purple-300 uppercase tracking-widest mb-2 px-1">
                    Reason
                  </label>
                  <select
                    value={reportReason}
                    onChange={(e) => setReportReason(e.target.value)}
                    className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white appearance-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  >
                    <option value="" className="bg-[#0f0c29]">Select a reason</option>
                    <option value="spam" className="bg-[#0f0c29]">Spam</option>
                    <option value="hate_speech" className="bg-[#0f0c29]">Hate Speech</option>
                    <option value="harassment" className="bg-[#0f0c29]">Harassment</option>
                    <option value="misinformation" className="bg-[#0f0c29]">Misinformation</option>
                    <option value="other" className="bg-[#0f0c29]">Other</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-black text-purple-300 uppercase tracking-widest mb-2 px-1">
                    Description (optional)
                  </label>
                  <textarea
                    value={reportDescription}
                    onChange={(e) => setReportDescription(e.target.value)}
                    className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/20 focus:ring-2 focus:ring-purple-500 focus:border-transparent h-32 resize-none"
                    placeholder="Describe the anomaly..."
                  />
                </div>

                <div className="flex space-x-3 pt-4">
                  <button
                    onClick={() => setReportingPost(null)}
                    className="flex-1 px-4 py-3 border border-white/10 rounded-xl text-white hover:bg-white/5 transition-colors font-bold uppercase tracking-widest text-xs"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleReportPost}
                    disabled={!reportReason}
                    className="flex-1 px-4 py-3 bg-gradient-to-r from-red-600 to-red-800 text-white rounded-xl hover:from-red-700 hover:to-red-900 transition-all font-bold uppercase tracking-widest text-xs shadow-lg disabled:opacity-20"
                  >
                    Submit Report
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};


export default SocialModerationPlatform;
