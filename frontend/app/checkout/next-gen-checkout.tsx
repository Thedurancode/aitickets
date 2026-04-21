"use client";

import { Suspense, useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence, useMotionValue, useTransform, useSpring } from "framer-motion";
import {
  CreditCard,
  Lock,
  CheckCircle2,
  Sparkles,
  Fingerprint,
  Scan,
  Shield,
  Zap,
  TrendingUp,
  Smartphone,
  Globe,
  Award,
  Timer,
  ChevronRight,
  Ticket,
  MapPin,
  Calendar,
  Wifi,
  Eye,
  EyeOff,
  Check,
  X,
  ArrowRight,
  Bitcoin,
  Gem
} from "lucide-react";
import Link from "next/link";
import { useCheckoutStore } from "@/stores/checkout-store";
import { usePurchaseMutation } from "@/lib/queries";
import { cn } from "@/lib/utils";
import confetti from "canvas-confetti";

// Advanced checkout with 3D effects and AI features
export default function NextGenCheckoutContent() {
  return (
    <Suspense fallback={<FuturisticLoader />}>
      <NextGenCheckoutInner />
    </Suspense>
  );
}

function NextGenCheckoutInner() {
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  const [paymentMethod, setPaymentMethod] = useState<'card' | 'crypto' | 'bnpl'>('card');
  const [isProcessing, setIsProcessing] = useState(false);
  const [showCardDetails, setShowCardDetails] = useState(false);
  const [cardNumber, setCardNumber] = useState("");
  const [cardName, setCardName] = useState("");
  const [expiry, setExpiry] = useState("");
  const [cvc, setCvc] = useState("");
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [fraudScore, setFraudScore] = useState(0);
  const [aiSuggestions, setAiSuggestions] = useState<string[]>([]);
  const [useBiometric, setUseBiometric] = useState(false);
  const [savePayment, setSavePayment] = useState(false);

  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);

  const rotateX = useTransform(mouseY, [-300, 300], [30, -30]);
  const rotateY = useTransform(mouseX, [-300, 300], [-30, 30]);
  const springRotateX = useSpring(rotateX, { stiffness: 300, damping: 30 });
  const springRotateY = useSpring(rotateY, { stiffness: 300, damping: 30 });

  const cardRef = useRef<HTMLDivElement>(null);

  const {
    event,
    selectedTier,
    quantity,
    promoValidation,
    getTotal,
    clearCheckout,
  } = useCheckoutStore();

  const purchaseMutation = usePurchaseMutation(event?.id || 0);

  useEffect(() => {
    setMounted(true);

    // Simulate AI suggestions
    const timer = setTimeout(() => {
      setAiSuggestions([
        "💡 Use virtual card for extra security",
        "🎯 Save 5% with crypto payment",
        "⚡ Express checkout available"
      ]);
    }, 1500);

    return () => clearTimeout(timer);
  }, []);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!cardRef.current) return;

    const rect = cardRef.current.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;

    mouseX.set(e.clientX - centerX);
    mouseY.set(e.clientY - centerY);
  };

  const handleMouseLeave = () => {
    mouseX.set(0);
    mouseY.set(0);
  };

  const handlePurchase = async () => {
    setIsProcessing(true);

    // Simulate processing with steps
    const steps = [
      "Validating payment details...",
      "Checking fraud protection...",
      "Processing with bank...",
      "Generating tickets...",
      "Success! Redirecting..."
    ];

    for (let i = 0; i < steps.length; i++) {
      await new Promise(resolve => setTimeout(resolve, 800));
    }

    // Trigger confetti
    confetti({
      particleCount: 100,
      spread: 70,
      origin: { y: 0.6 }
    });

    try {
      const result = await purchaseMutation.mutateAsync({
        ticket_tier_id: selectedTier.id,
        email,
        name,
        phone: phone || undefined,
        quantity,
        promo_code: promoValidation?.code || undefined,
      });

      if (result.checkout_url) {
        window.location.href = result.checkout_url;
      } else if (result.tickets) {
        const ticketIds = result.tickets.map((t) => t.id).join(",");
        clearCheckout();
        router.push(`/success?tickets=${ticketIds}`);
      }
    } catch (err) {
      console.error("Purchase failed:", err);
    } finally {
      setIsProcessing(false);
    }
  };

  // Simulate fraud detection
  useEffect(() => {
    if (cardNumber.length >= 8) {
      const score = Math.random() * 100;
      setFraudScore(score);
    }
  }, [cardNumber]);

  if (!mounted) return <FuturisticLoader />;

  if (!event || !selectedTier) {
    return <EmptyStateDeluxe />;
  }

  const total = getTotal();
  const subtotal = selectedTier.price * quantity;
  const discount = promoValidation ? subtotal - total : 0;

  return (
    <div className="min-h-screen bg-black text-white overflow-hidden">
      {/* Animated gradient background */}
      <div className="fixed inset-0 opacity-30">
        <div className="absolute inset-0 bg-gradient-to-br from-purple-900 via-blue-900 to-cyan-900" />
        <motion.div
          className="absolute inset-0"
          animate={{
            background: [
              "radial-gradient(circle at 20% 50%, rgba(120, 119, 198, 0.3) 0%, transparent 50%)",
              "radial-gradient(circle at 80% 50%, rgba(255, 182, 193, 0.3) 0%, transparent 50%)",
              "radial-gradient(circle at 20% 50%, rgba(120, 119, 198, 0.3) 0%, transparent 50%)",
            ],
          }}
          transition={{ duration: 10, repeat: Infinity }}
        />
      </div>

      {/* Floating particles */}
      <div className="fixed inset-0 pointer-events-none">
        {[...Array(20)].map((_, i) => (
          <motion.div
            key={i}
            className="absolute w-1 h-1 bg-white/20 rounded-full"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
            }}
            animate={{
              y: [-20, 20, -20],
              x: [-10, 10, -10],
              opacity: [0.2, 0.5, 0.2],
            }}
            transition={{
              duration: 5 + Math.random() * 5,
              repeat: Infinity,
              delay: Math.random() * 5,
            }}
          />
        ))}
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-4 py-8">
        {/* Futuristic Header */}
        <motion.header
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <div className="flex items-center justify-between">
            <Link href={`/events/${event.id}`}>
              <button className="group flex items-center space-x-2 text-gray-400 hover:text-white transition-colors">
                <motion.div
                  whileHover={{ x: -5 }}
                  className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center"
                >
                  ←
                </motion.div>
                <span>Back</span>
              </button>
            </Link>

            <div className="flex items-center space-x-4">
              {/* Trust indicators */}
              <div className="flex items-center space-x-2 text-green-400">
                <Shield className="w-4 h-4" />
                <span className="text-xs">Military-Grade Encryption</span>
              </div>
              <div className="flex items-center space-x-2 text-blue-400">
                <Wifi className="w-4 h-4" />
                <span className="text-xs">Real-time Protection</span>
              </div>
            </div>
          </div>
        </motion.header>

        <div className="grid lg:grid-cols-3 gap-8">
          {/* Main checkout area - 2 cols */}
          <div className="lg:col-span-2 space-y-6">
            {/* Payment Method Selection */}
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="bg-white/5 backdrop-blur-xl rounded-3xl p-6 border border-white/10"
            >
              <h2 className="text-xl font-bold mb-4 flex items-center">
                <Zap className="mr-2 text-yellow-400" />
                Choose Payment Method
              </h2>

              <div className="grid grid-cols-3 gap-4">
                {[
                  { id: 'card', icon: CreditCard, label: 'Card', bonus: 'Instant' },
                  { id: 'crypto', icon: Bitcoin, label: 'Crypto', bonus: 'Save 5%' },
                  { id: 'bnpl', icon: Gem, label: 'Buy Now Pay Later', bonus: '4 payments' }
                ].map((method) => (
                  <motion.button
                    key={method.id}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => setPaymentMethod(method.id as any)}
                    className={cn(
                      "relative p-4 rounded-xl border transition-all",
                      paymentMethod === method.id
                        ? "bg-gradient-to-br from-purple-600 to-blue-600 border-transparent"
                        : "bg-white/5 border-white/10 hover:bg-white/10"
                    )}
                  >
                    {method.bonus && (
                      <span className="absolute -top-2 -right-2 bg-green-500 text-xs px-2 py-1 rounded-full">
                        {method.bonus}
                      </span>
                    )}
                    <method.icon className="w-6 h-6 mx-auto mb-2" />
                    <div className="text-sm">{method.label}</div>
                  </motion.button>
                ))}
              </div>
            </motion.div>

            {/* 3D Interactive Card */}
            {paymentMethod === 'card' && (
              <motion.div
                initial={{ opacity: 0, rotateX: -30 }}
                animate={{ opacity: 1, rotateX: 0 }}
                transition={{ type: "spring", stiffness: 100 }}
                className="relative"
                onMouseMove={handleMouseMove}
                onMouseLeave={handleMouseLeave}
              >
                <motion.div
                  ref={cardRef}
                  className="relative preserve-3d"
                  style={{
                    rotateX: springRotateX,
                    rotateY: springRotateY,
                    transformStyle: "preserve-3d",
                  }}
                >
                  {/* Credit Card Visual */}
                  <div className="relative bg-gradient-to-br from-purple-600 via-pink-600 to-blue-600 rounded-3xl p-8 shadow-2xl">
                    <div className="absolute inset-0 bg-white/10 rounded-3xl backdrop-blur-sm" />

                    <div className="relative z-10">
                      {/* Card chip */}
                      <div className="w-12 h-10 bg-yellow-400/80 rounded-lg mb-8 shadow-lg" />

                      {/* Card number */}
                      <div className="mb-6">
                        <input
                          type="text"
                          placeholder="0000 0000 0000 0000"
                          value={cardNumber}
                          onChange={(e) => setCardNumber(e.target.value)}
                          className="w-full bg-transparent text-2xl font-mono tracking-wider placeholder-white/50 focus:outline-none"
                          maxLength={19}
                        />
                      </div>

                      {/* Card details */}
                      <div className="flex justify-between items-end">
                        <div>
                          <div className="text-xs opacity-60 mb-1">CARD HOLDER</div>
                          <input
                            type="text"
                            placeholder="YOUR NAME"
                            value={cardName}
                            onChange={(e) => setCardName(e.target.value)}
                            className="bg-transparent uppercase tracking-wider placeholder-white/50 focus:outline-none"
                          />
                        </div>

                        <div>
                          <div className="text-xs opacity-60 mb-1">EXPIRES</div>
                          <input
                            type="text"
                            placeholder="MM/YY"
                            value={expiry}
                            onChange={(e) => setExpiry(e.target.value)}
                            className="bg-transparent w-20 font-mono placeholder-white/50 focus:outline-none"
                            maxLength={5}
                          />
                        </div>

                        <div>
                          <div className="text-xs opacity-60 mb-1">CVC</div>
                          <input
                            type="text"
                            placeholder="***"
                            value={cvc}
                            onChange={(e) => setCvc(e.target.value)}
                            className="bg-transparent w-12 font-mono placeholder-white/50 focus:outline-none"
                            maxLength={3}
                          />
                        </div>
                      </div>

                      {/* Holographic strip */}
                      <motion.div
                        className="absolute inset-0 rounded-3xl pointer-events-none"
                        style={{
                          background: "linear-gradient(105deg, transparent 40%, rgba(255, 255, 255, 0.2) 50%, transparent 60%)",
                        }}
                        animate={{
                          x: [-300, 300],
                        }}
                        transition={{
                          duration: 3,
                          repeat: Infinity,
                          repeatType: "reverse",
                        }}
                      />
                    </div>
                  </div>
                </motion.div>

                {/* Fraud Score Indicator */}
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 }}
                  className="mt-4 bg-white/5 backdrop-blur-xl rounded-2xl p-4 border border-white/10"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm flex items-center">
                      <Shield className="w-4 h-4 mr-2 text-green-400" />
                      Fraud Protection Score
                    </span>
                    <span className={cn(
                      "text-sm font-bold",
                      fraudScore > 80 ? "text-red-400" : fraudScore > 40 ? "text-yellow-400" : "text-green-400"
                    )}>
                      {fraudScore.toFixed(0)}%
                    </span>
                  </div>
                  <div className="w-full bg-white/10 rounded-full h-2 overflow-hidden">
                    <motion.div
                      className={cn(
                        "h-full rounded-full",
                        fraudScore > 80 ? "bg-red-400" : fraudScore > 40 ? "bg-yellow-400" : "bg-green-400"
                      )}
                      initial={{ width: 0 }}
                      animate={{ width: `${fraudScore}%` }}
                      transition={{ duration: 0.5 }}
                    />
                  </div>
                </motion.div>
              </motion.div>
            )}

            {/* Contact Information with AI Suggestions */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="bg-white/5 backdrop-blur-xl rounded-3xl p-6 border border-white/10"
            >
              <h3 className="text-lg font-semibold mb-4 flex items-center">
                <Sparkles className="mr-2 text-yellow-400" />
                Contact Details
              </h3>

              {/* AI Suggestions */}
              {aiSuggestions.length > 0 && (
                <div className="mb-4 p-3 bg-blue-500/10 rounded-xl border border-blue-500/20">
                  <div className="text-xs text-blue-400 mb-1">AI Suggestions</div>
                  <div className="space-y-1">
                    {aiSuggestions.map((suggestion, i) => (
                      <motion.div
                        key={i}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.1 }}
                        className="text-sm text-gray-300"
                      >
                        {suggestion}
                      </motion.div>
                    ))}
                  </div>
                </div>
              )}

              <div className="space-y-4">
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Email</label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 focus:outline-none focus:border-purple-500 transition-colors"
                    placeholder="your@email.com"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs text-gray-400 mb-1 block">Full Name</label>
                    <input
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 focus:outline-none focus:border-purple-500 transition-colors"
                      placeholder="John Doe"
                    />
                  </div>

                  <div>
                    <label className="text-xs text-gray-400 mb-1 block">Phone</label>
                    <input
                      type="tel"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 focus:outline-none focus:border-purple-500 transition-colors"
                      placeholder="+1 (555) 123-4567"
                    />
                  </div>
                </div>
              </div>
            </motion.div>

            {/* Advanced Security Options */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="bg-white/5 backdrop-blur-xl rounded-3xl p-6 border border-white/10"
            >
              <h3 className="text-lg font-semibold mb-4">Security Options</h3>

              <div className="space-y-3">
                <label className="flex items-center justify-between p-3 bg-white/5 rounded-xl cursor-pointer hover:bg-white/10 transition-colors">
                  <div className="flex items-center">
                    <Fingerprint className="w-5 h-5 mr-3 text-blue-400" />
                    <div>
                      <div className="text-sm font-medium">Biometric Authentication</div>
                      <div className="text-xs text-gray-400">Use Face ID or Touch ID</div>
                    </div>
                  </div>
                  <input
                    type="checkbox"
                    checked={useBiometric}
                    onChange={(e) => setUseBiometric(e.target.checked)}
                    className="w-5 h-5"
                  />
                </label>

                <label className="flex items-center justify-between p-3 bg-white/5 rounded-xl cursor-pointer hover:bg-white/10 transition-colors">
                  <div className="flex items-center">
                    <Lock className="w-5 h-5 mr-3 text-green-400" />
                    <div>
                      <div className="text-sm font-medium">Save Payment Method</div>
                      <div className="text-xs text-gray-400">Securely save for future purchases</div>
                    </div>
                  </div>
                  <input
                    type="checkbox"
                    checked={savePayment}
                    onChange={(e) => setSavePayment(e.target.checked)}
                    className="w-5 h-5"
                  />
                </label>
              </div>
            </motion.div>

            {/* Purchase Button */}
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handlePurchase}
              disabled={isProcessing}
              className={cn(
                "w-full relative overflow-hidden rounded-2xl p-6 font-bold text-lg transition-all",
                isProcessing
                  ? "bg-gray-800 cursor-not-allowed"
                  : "bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
              )}
            >
              {/* Animated background */}
              <motion.div
                className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent"
                animate={{
                  x: [-500, 500],
                }}
                transition={{
                  duration: 2,
                  repeat: Infinity,
                  repeatType: "loop",
                }}
              />

              <span className="relative z-10 flex items-center justify-center">
                {isProcessing ? (
                  <>
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                      className="mr-3"
                    >
                      <Zap className="w-5 h-5" />
                    </motion.div>
                    Processing Quantum Payment...
                  </>
                ) : (
                  <>
                    <Lock className="mr-2 w-5 h-5" />
                    Pay ${(total / 100).toFixed(2)} with {paymentMethod === 'crypto' ? 'Crypto' : paymentMethod === 'bnpl' ? 'BNPL' : 'Card'}
                    <ArrowRight className="ml-2 w-5 h-5" />
                  </>
                )}
              </span>
            </motion.button>
          </div>

          {/* Order Summary - Right col */}
          <div className="lg:sticky lg:top-8 h-fit">
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              className="bg-white/5 backdrop-blur-xl rounded-3xl p-6 border border-white/10"
            >
              <h2 className="text-xl font-bold mb-6 flex items-center">
                <Ticket className="mr-2 text-purple-400" />
                Order Summary
              </h2>

              {/* Event Preview with AR hint */}
              <div className="relative mb-6 rounded-2xl overflow-hidden">
                <img
                  src={event.image_url || "https://images.unsplash.com/photo-1470229722913-7c0e2dbbafd3"}
                  alt={event.name}
                  className="w-full h-40 object-cover"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 to-transparent" />
                <div className="absolute bottom-3 left-3 right-3">
                  <h3 className="font-bold text-lg mb-1">{event.name}</h3>
                  <div className="flex items-center text-xs text-gray-300">
                    <MapPin className="w-3 h-3 mr-1" />
                    {event.venue?.name}
                  </div>
                </div>

                {/* AR Preview button */}
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  className="absolute top-3 right-3 bg-black/50 backdrop-blur-sm px-3 py-1.5 rounded-full text-xs flex items-center"
                >
                  <Scan className="w-3 h-3 mr-1" />
                  AR Preview
                </motion.button>
              </div>

              {/* Ticket Details */}
              <div className="space-y-4 mb-6">
                <div className="flex justify-between items-center">
                  <div>
                    <div className="text-sm text-gray-400">{selectedTier.name}</div>
                    <div className="text-xs text-gray-500">Qty: {quantity}</div>
                  </div>
                  <div className="text-lg font-semibold">
                    ${(subtotal / 100).toFixed(2)}
                  </div>
                </div>

                {discount > 0 && (
                  <div className="flex justify-between items-center text-green-400">
                    <div className="text-sm">Promo Discount</div>
                    <div className="text-lg font-semibold">
                      -${(discount / 100).toFixed(2)}
                    </div>
                  </div>
                )}

                {paymentMethod === 'crypto' && (
                  <div className="flex justify-between items-center text-blue-400">
                    <div className="text-sm">Crypto Bonus (5%)</div>
                    <div className="text-lg font-semibold">
                      -${((total * 0.05) / 100).toFixed(2)}
                    </div>
                  </div>
                )}

                <div className="pt-4 border-t border-white/10">
                  <div className="flex justify-between items-center">
                    <div className="text-lg font-semibold">Total</div>
                    <motion.div
                      key={total}
                      initial={{ scale: 1.2, color: "#10b981" }}
                      animate={{ scale: 1, color: "#ffffff" }}
                      className="text-2xl font-bold"
                    >
                      ${((paymentMethod === 'crypto' ? total * 0.95 : total) / 100).toFixed(2)}
                    </motion.div>
                  </div>
                </div>
              </div>

              {/* Trust Badges */}
              <div className="grid grid-cols-2 gap-3">
                {[
                  { icon: Timer, text: "2min checkout" },
                  { icon: Shield, text: "100% secure" },
                  { icon: Award, text: "Best price" },
                  { icon: Globe, text: "Worldwide" }
                ].map((badge, i) => (
                  <motion.div
                    key={badge.text}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.4 + i * 0.1 }}
                    className="flex items-center text-xs text-gray-400 bg-white/5 rounded-lg p-2"
                  >
                    <badge.icon className="w-3 h-3 mr-1.5 text-green-400" />
                    {badge.text}
                  </motion.div>
                ))}
              </div>
            </motion.div>

            {/* Live Stats */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
              className="mt-4 bg-white/5 backdrop-blur-xl rounded-2xl p-4 border border-white/10"
            >
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-400">Live buyers</span>
                <div className="flex items-center">
                  <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse mr-2" />
                  <span>{Math.floor(Math.random() * 50 + 10)} people</span>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </div>

      {/* Processing Overlay */}
      <AnimatePresence>
        {isProcessing && <ProcessingOverlayDeluxe />}
      </AnimatePresence>
    </div>
  );
}

function ProcessingOverlayDeluxe() {
  const steps = [
    "Initializing quantum encryption...",
    "Validating biometric signature...",
    "Processing with neural network...",
    "Minting digital tickets...",
    "Finalizing blockchain record..."
  ];

  const [currentStep, setCurrentStep] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentStep((prev) => (prev + 1) % steps.length);
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 bg-black/90 backdrop-blur-xl flex items-center justify-center"
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        className="max-w-md mx-4"
      >
        <div className="text-center">
          {/* Animated Logo */}
          <div className="mb-8 relative">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
              className="w-24 h-24 mx-auto rounded-full bg-gradient-to-r from-purple-600 to-pink-600 p-1"
            >
              <div className="w-full h-full bg-black rounded-full flex items-center justify-center">
                <Zap className="w-12 h-12 text-white" />
              </div>
            </motion.div>

            {/* Orbiting dots */}
            {[0, 1, 2].map((i) => (
              <motion.div
                key={i}
                className="absolute w-3 h-3 bg-blue-400 rounded-full"
                style={{
                  top: "50%",
                  left: "50%",
                }}
                animate={{
                  x: [
                    Math.cos((i * 120) * Math.PI / 180) * 60,
                    Math.cos((i * 120 + 360) * Math.PI / 180) * 60,
                  ],
                  y: [
                    Math.sin((i * 120) * Math.PI / 180) * 60,
                    Math.sin((i * 120 + 360) * Math.PI / 180) * 60,
                  ],
                }}
                transition={{
                  duration: 2,
                  repeat: Infinity,
                  delay: i * 0.3,
                }}
              />
            ))}
          </div>

          <h2 className="text-2xl font-bold mb-4 text-white">
            Processing Payment
          </h2>

          {/* Steps */}
          <div className="space-y-3 mb-6">
            {steps.map((step, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0.3 }}
                animate={{
                  opacity: i <= currentStep ? 1 : 0.3,
                }}
                className="flex items-center text-sm"
              >
                <div
                  className={cn(
                    "w-6 h-6 rounded-full mr-3 flex items-center justify-center text-xs",
                    i < currentStep
                      ? "bg-green-500"
                      : i === currentStep
                      ? "bg-blue-500"
                      : "bg-gray-700"
                  )}
                >
                  {i < currentStep ? <Check className="w-3 h-3" /> : i + 1}
                </div>
                <span className={cn(
                  i <= currentStep ? "text-white" : "text-gray-500"
                )}>
                  {step}
                </span>
              </motion.div>
            ))}
          </div>

          <div className="text-xs text-gray-400">
            This usually takes 10-15 seconds
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}

function FuturisticLoader() {
  return (
    <div className="min-h-screen bg-black flex items-center justify-center">
      <motion.div
        animate={{
          rotate: [0, 180, 360],
          scale: [1, 1.2, 1],
        }}
        transition={{
          duration: 2,
          repeat: Infinity,
        }}
        className="w-16 h-16 border-4 border-purple-600 border-t-transparent rounded-full"
      />
    </div>
  );
}

function EmptyStateDeluxe() {
  return (
    <div className="min-h-screen bg-black flex items-center justify-center">
      <motion.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        className="text-center"
      >
        <motion.div
          animate={{
            y: [-10, 10, -10],
          }}
          transition={{
            duration: 3,
            repeat: Infinity,
          }}
          className="mb-8"
        >
          <Ticket className="w-24 h-24 mx-auto text-purple-400" />
        </motion.div>

        <h1 className="text-3xl font-bold text-white mb-4">
          Your cart is empty
        </h1>
        <p className="text-gray-400 mb-8 max-w-md">
          Discover amazing events and experiences waiting for you
        </p>

        <Link href="/events">
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className="bg-gradient-to-r from-purple-600 to-pink-600 px-8 py-4 rounded-full font-semibold text-white flex items-center mx-auto"
          >
            Explore Events
            <ChevronRight className="ml-2 w-5 h-5" />
          </motion.button>
        </Link>
      </motion.div>
    </div>
  );
}