import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, Send, Loader2, DollarSign, Clock, Package, Lock, AlertTriangle, CreditCard } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Avatar, AvatarFallback, AvatarImage } from '../components/ui/avatar';
import { Badge } from '../components/ui/badge';
import { campaignsAPI, messagesAPI, paymentsAPI } from '../lib/api';
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
  const [payingEscrow, setPayingEscrow] = useState(false);
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
      const [campaignRes, messagesRes] = await Promise.all([
        campaignsAPI.getById(requestId),
        messagesAPI.getMessages(requestId)
      ]);
      setCampaign(campaignRes.data);
      setMessages(messagesRes.data);
    } catch (error) {
      toast.error("Failed to load chat");
      navigate(-1);
    } finally {
      setLoading(false);
    }
  };

  const loadMessages = async () => {
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
      if (response.data.isBlocked) {
        toast.warning("Message blocked - external contact sharing is not allowed before payment");
      }
    } catch (error) {
      toast.error("Failed to send message");
    } finally {
      setSending(false);
    }
  };

  const handlePayEscrow = async () => {
    setPayingEscrow(true);
    try {
      const orderRes = await paymentsAPI.createEscrowOrder(requestId);
      const { orderId, amount, keyId } = orderRes.data;

      if (!keyId) {
        toast.error("Payment not configured. Contact admin.");
        setPayingEscrow(false);
        return;
      }

      const options = {
        key: keyId,
        amount: amount,
        currency: "INR",
        name: "Orange",
        description: `Campaign Payment - ${campaign.title}`,
        order_id: orderId,
        handler: async (response) => {
          try {
            await paymentsAPI.verifyEscrowPayment(requestId, {
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature
            });
            toast.success("Payment successful! Full access unlocked 🎉");
            loadData(); // Refresh campaign
          } catch (err) {
            toast.error("Payment verification failed");
          }
        },
        prefill: {
          email: user?.email || ""
        },
        theme: {
          color: "#FF6B00"
        }
      };

      const razorpay = new window.Razorpay(options);
      razorpay.open();
    } catch (error) {
      toast.error("Failed to create payment order");
    } finally {
      setPayingEscrow(false);
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
  const otherParty = isCreator 
    ? { name: campaign?.brandName, photo: null }
    : { name: campaign?.creatorName, photo: null };
  
  const escrowPaid = campaign?.escrowStatus === 'paid' || campaign?.escrowStatus === 'released';
  const canPayEscrow = isBrand && campaign?.campaignStatus === 'accepted' && campaign?.escrowStatus === 'pending';

  return (
    <div className="h-screen flex flex-col bg-background">
      {/* Header */}
      <header className="border-b border-orange-100 bg-white/80 backdrop-blur-sm px-4 py-3">
        <div className="max-w-4xl mx-auto flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-full" onClick={() => navigate(-1)} data-testid="back-btn">
            <ArrowLeft className="w-5 h-5" />
          </Button>
          
          <Avatar className="w-10 h-10 border-2 border-orange-100">
            <AvatarImage src={otherParty.photo} />
            <AvatarFallback className="bg-primary/10 text-primary">
              {otherParty.name?.[0]}
            </AvatarFallback>
          </Avatar>
          
          <div className="flex-1">
            <h2 className="font-semibold">{otherParty.name}</h2>
            <p className="text-xs text-muted-foreground">{campaign?.title}</p>
          </div>
          
          <div className="flex gap-2">
            <Badge className={
              campaign?.campaignStatus === 'accepted' ? 'bg-green-100 text-green-800' :
              campaign?.campaignStatus === 'proposed' ? 'bg-blue-100 text-blue-800' :
              campaign?.campaignStatus === 'in_progress' ? 'bg-yellow-100 text-yellow-800' :
              'bg-gray-100 text-gray-800'
            }>
              {campaign?.campaignStatus?.replace('_', ' ')}
            </Badge>
            <Badge className={escrowPaid ? 'bg-green-100 text-green-800' : 'bg-orange-100 text-orange-800'}>
              {escrowPaid ? '💰 Paid' : '⏳ Awaiting Payment'}
            </Badge>
          </div>
        </div>
      </header>

      {/* Campaign Details Card */}
      <div className="bg-muted/30 border-b border-orange-100 px-4 py-3">
        <div className="max-w-4xl mx-auto">
          <div className="card-orange p-4">
            <h3 className="font-heading font-bold mb-2">{campaign?.title}</h3>
            <p className="text-sm text-muted-foreground mb-3">{campaign?.brief}</p>
            <div className="flex flex-wrap gap-4 text-sm">
              {campaign?.price > 0 && (
                <div className="flex items-center gap-1 text-primary font-semibold">
                  <DollarSign className="w-4 h-4" />
                  {formatPrice(campaign.price)}
                </div>
              )}
              {campaign?.deliverables && (
                <div className="flex items-center gap-1 text-muted-foreground">
                  <Package className="w-4 h-4" />
                  {campaign.deliverables}
                </div>
              )}
              {campaign?.timeline && (
                <div className="flex items-center gap-1 text-muted-foreground">
                  <Clock className="w-4 h-4" />
                  {campaign.timeline}
                </div>
              )}
              {campaign?.isBarter && (
                <Badge className="bg-accent/50">🤝 Barter Deal</Badge>
              )}
            </div>
            
            {/* Pay Escrow Button for Brands */}
            {canPayEscrow && (
              <div className="mt-4 pt-4 border-t border-orange-100">
                <Button 
                  onClick={handlePayEscrow} 
                  className="w-full btn-primary"
                  disabled={payingEscrow}
                  data-testid="pay-escrow-btn"
                >
                  {payingEscrow ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <CreditCard className="w-4 h-4 mr-2" />
                  )}
                  Pay {formatPrice(campaign.price)} to Unlock Full Access
                </Button>
                <p className="text-xs text-muted-foreground text-center mt-2">
                  Payment held in escrow. Released after you approve the delivery.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Chat Restriction Warning */}
      {!escrowPaid && (
        <div className="bg-orange-50 border-b border-orange-200 px-4 py-2">
          <div className="max-w-4xl mx-auto flex items-center gap-2 text-sm text-orange-800">
            <AlertTriangle className="w-4 h-4" />
            <span>External contact sharing (Instagram, phone, etc.) is blocked until escrow payment</span>
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
              const isOwnMessage = message.senderUserId === user?.id;
              const isSystemMessage = message.senderUserId === 'system';
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
                  
                  {isSystemMessage ? (
                    // System warning message
                    <div className="flex justify-center">
                      <div className="bg-orange-50 border border-orange-200 rounded-xl px-4 py-2 max-w-md">
                        <p className="text-sm text-orange-800 flex items-center gap-2">
                          <AlertTriangle className="w-4 h-4" />
                          {message.text}
                        </p>
                      </div>
                    </div>
                  ) : (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className={`flex ${isOwnMessage ? 'justify-end' : 'justify-start'}`}
                    >
                      <div className={`flex gap-2 max-w-[75%] ${isOwnMessage ? 'flex-row-reverse' : ''}`}>
                        {!isOwnMessage && (
                          <Avatar className="w-8 h-8 border border-orange-100">
                            <AvatarFallback className="bg-primary/10 text-primary text-xs">
                              {message.senderName?.[0]}
                            </AvatarFallback>
                          </Avatar>
                        )}
                        <div>
                          <div className={`px-4 py-2 rounded-2xl ${
                            message.isBlocked 
                              ? 'bg-red-50 border border-red-200 text-red-800'
                              : isOwnMessage 
                                ? 'bg-primary text-white rounded-tr-none' 
                                : 'bg-white border border-orange-100 rounded-tl-none'
                          }`}>
                            {message.isBlocked && (
                              <div className="flex items-center gap-1 text-xs mb-1 text-red-600">
                                <Lock className="w-3 h-3" />
                                Blocked
                              </div>
                            )}
                            <p className="text-sm">{message.text}</p>
                          </div>
                          <p className={`text-xs text-muted-foreground mt-1 ${isOwnMessage ? 'text-right' : ''}`}>
                            {formatTime(message.createdAt)}
                          </p>
                        </div>
                      </div>
                    </motion.div>
                  )}
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
            placeholder={escrowPaid ? "Type your message..." : "Type your message (external contacts blocked)..."}
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
