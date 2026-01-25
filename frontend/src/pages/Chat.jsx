import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, Send, Loader2, Clock, Lock, AlertTriangle, CheckCircle } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Avatar, AvatarFallback, AvatarImage } from '../components/ui/avatar';
import { Badge } from '../components/ui/badge';
import { campaignAPI, messagesAPI, getErrorMessage } from '../lib/api';
import { useAuth } from '../lib/auth';
import { toast } from 'sonner';

const Chat = () => {
  const { requestId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [campaign, setCampaign] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadMessages, 5000);
    return () => clearInterval(interval);
  }, [requestId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const loadData = async () => {
    try {
      const campaignRes = await campaignAPI.getById(requestId);
      setCampaign(campaignRes.data);
      
      // Only load messages if chat is enabled
      if (campaignRes.data.chatEnabled) {
        const messagesRes = await messagesAPI.getMessages(requestId);
        setMessages(messagesRes.data);
      }
    } catch (error) {
      toast.error(getErrorMessage(error, "Failed to load chat"));
      navigate(-1);
    } finally {
      setLoading(false);
    }
  };

  const loadMessages = async () => {
    if (!campaign?.chatEnabled) return;
    try {
      const response = await messagesAPI.getMessages(requestId);
      setMessages(response.data);
    } catch (error) {
      // Silent fail for polling
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSend = async (e) => {
    e.preventDefault();
    if (!newMessage.trim()) return;

    setSending(true);
    try {
      const response = await messagesAPI.sendMessage(requestId, newMessage);
      setMessages(prev => [...prev, response.data]);
      setNewMessage('');
      
      // Check if message was blocked
      if (response.data.blocked) {
        toast.warning("Message blocked - external contact sharing is not allowed");
      }
    } catch (error) {
      toast.error(getErrorMessage(error, "Failed to send message"));
    } finally {
      setSending(false);
    }
  };

  const formatPrice = (price) => {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(price);
  };

  const formatTime = (dateString) => {
    return new Date(dateString).toLocaleTimeString('en-IN', { 
      hour: '2-digit', 
      minute: '2-digit',
      hour12: true 
    });
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    
    if (date.toDateString() === today.toDateString()) return 'Today';
    if (date.toDateString() === yesterday.toDateString()) return 'Yesterday';
    return date.toLocaleDateString('en-IN', { month: 'short', day: 'numeric' });
  };

  if (loading) {
    return (
      <div className="min-h-screen gradient-hero flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-10 h-10 mx-auto text-primary animate-spin mb-4" />
          <p className="text-muted-foreground">Loading chat...</p>
        </div>
      </div>
    );
  }

  const isCreator = user?.role === 'creator';
  const isBrand = user?.role === 'business';
  const otherPartyName = isCreator ? campaign?.senderName : campaign?.receiverName;
  const otherPartyInstagram = isCreator ? campaign?.senderInstagram : campaign?.receiverInstagram;
  
  // Check if chat is enabled (after payment)
  if (!campaign?.chatEnabled) {
    return (
      <div className="h-screen flex flex-col bg-background">
        <header className="border-b border-orange-100 bg-white/80 backdrop-blur-sm px-4 py-3">
          <div className="max-w-4xl mx-auto flex items-center gap-4">
            <Button variant="ghost" size="icon" className="rounded-full" onClick={() => navigate(-1)}>
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <h2 className="font-semibold">Chat</h2>
          </div>
        </header>
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center p-8">
            <Lock className="w-16 h-16 mx-auto text-muted-foreground mb-4" />
            <h3 className="font-heading text-xl font-bold mb-2">Chat Not Available</h3>
            <p className="text-muted-foreground">Chat will unlock after payment is completed.</p>
            <Button onClick={() => navigate(-1)} className="mt-4 btn-primary">
              Go Back
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-background">
      {/* Header */}
      <header className="border-b border-orange-100 bg-white/80 backdrop-blur-sm px-4 py-3">
        <div className="max-w-4xl mx-auto flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-full" onClick={() => navigate(-1)} data-testid="back-btn">
            <ArrowLeft className="w-5 h-5" />
          </Button>
          
          <Avatar className="w-10 h-10 border-2 border-orange-100">
            <AvatarFallback className="bg-primary/10 text-primary">
              {otherPartyName?.[0] || '?'}
            </AvatarFallback>
          </Avatar>
          
          <div className="flex-1">
            <h2 className="font-semibold">{otherPartyName}</h2>
            {campaign?.identityUnlocked && otherPartyInstagram && (
              <p className="text-xs text-green-600">IG: {otherPartyInstagram}</p>
            )}
          </div>
          
          <div className="flex gap-2">
            <Badge className={
              campaign?.status === 'completed' ? 'bg-green-500 text-white' :
              campaign?.status === 'paid' ? 'bg-purple-100 text-purple-800' :
              campaign?.status === 'link_submitted' ? 'bg-orange-100 text-orange-800' :
              'bg-gray-100 text-gray-800'
            }>
              {campaign?.status?.replace('_', ' ')}
            </Badge>
            {campaign?.identityUnlocked && (
              <Badge className="bg-green-100 text-green-800">🔓 Identity Unlocked</Badge>
            )}
          </div>
        </div>
      </header>

      {/* Campaign Details Card */}
      <div className="bg-muted/30 border-b border-orange-100 px-4 py-3">
        <div className="max-w-4xl mx-auto">
          <div className="card-orange p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="capitalize font-semibold">{campaign?.campaignType?.replace('_', ' ')}</span>
              {campaign?.campaignType === 'paid' && (
                <span className="text-primary font-bold">{formatPrice(campaign?.budget)}</span>
              )}
            </div>
            <p className="text-sm text-muted-foreground mb-2"><strong>Deliverables:</strong> {campaign?.deliverables}</p>
            {campaign?.contentLink && (
              <p className="text-sm text-blue-600">
                <strong>Link:</strong> <a href={campaign.contentLink} target="_blank" rel="noopener noreferrer" className="underline">{campaign.contentLink}</a>
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Chat Restriction Warning */}
      {!campaign?.identityUnlocked && (
        <div className="bg-orange-50 border-b border-orange-200 px-4 py-2">
          <div className="max-w-4xl mx-auto flex items-center gap-2 text-sm text-orange-800">
            <AlertTriangle className="w-4 h-4" />
            <span>External contact sharing (Instagram, phone, etc.) is blocked until identity unlock</span>
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-4xl mx-auto space-y-4">
          {messages.length === 0 ? (
            <div className="text-center py-12">
              <span className="text-5xl block mb-4">💬</span>
              <p className="text-muted-foreground">No messages yet. Start the conversation!</p>
            </div>
          ) : (
            messages.map((message, idx) => {
              const isOwnMessage = message.senderId === user?.id;
              const showDateHeader = idx === 0 || 
                formatDate(messages[idx - 1].createdAt) !== formatDate(message.createdAt);
              
              return (
                <div key={message.id}>
                  {showDateHeader && (
                    <div className="flex items-center justify-center my-4">
                      <span className="bg-muted px-3 py-1 rounded-full text-xs text-muted-foreground">
                        {formatDate(message.createdAt)}
                      </span>
                    </div>
                  )}
                  
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`flex ${isOwnMessage ? 'justify-end' : 'justify-start'}`}
                  >
                    <div className={`flex gap-2 max-w-[75%] ${isOwnMessage ? 'flex-row-reverse' : ''}`}>
                      {!isOwnMessage && (
                        <Avatar className="w-8 h-8 border border-orange-100">
                          <AvatarFallback className="bg-primary/10 text-primary text-xs">
                            {otherPartyName?.[0] || '?'}
                          </AvatarFallback>
                        </Avatar>
                      )}
                      <div>
                        <div className={`px-4 py-2 rounded-2xl ${
                          message.blocked 
                            ? 'bg-red-50 border border-red-200 text-red-800'
                            : isOwnMessage 
                              ? 'bg-primary text-white rounded-tr-none' 
                              : 'bg-white border border-orange-100 rounded-tl-none'
                        }`}>
                          {message.blocked && (
                            <div className="flex items-center gap-1 text-xs mb-1 text-red-600">
                              <Lock className="w-3 h-3" />
                              Blocked
                            </div>
                          )}
                          <p className="text-sm">{message.content}</p>
                        </div>
                        <p className={`text-xs text-muted-foreground mt-1 ${isOwnMessage ? 'text-right' : ''}`}>
                          {formatTime(message.createdAt)}
                        </p>
                      </div>
                    </div>
                  </motion.div>
                </div>
              );
            })
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Message Input */}
      <div className="border-t border-orange-100 bg-white px-4 py-4">
        <form onSubmit={handleSend} className="max-w-4xl mx-auto flex gap-3">
          <Input
            value={newMessage}
            onChange={(e) => setNewMessage(e.target.value)}
            placeholder={campaign?.identityUnlocked ? "Type your message..." : "Type your message (external contacts blocked)..."}
            className="flex-1 input-orange"
            disabled={sending}
            data-testid="message-input"
          />
          <Button 
            type="submit" 
            className="btn-primary px-6" 
            disabled={sending || !newMessage.trim()}
            data-testid="send-message-btn"
          >
            {sending ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </Button>
        </form>
      </div>
    </div>
  );
};

export default Chat;
