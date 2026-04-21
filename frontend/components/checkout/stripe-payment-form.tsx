"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  CreditCard,
  Lock,
  CheckCircle,
  AlertCircle,
  Info
} from "lucide-react";
import { cn } from "@/lib/utils";

interface PaymentFieldProps {
  label: string;
  error?: string;
  focused?: boolean;
  icon?: React.ReactNode;
  helper?: string;
  required?: boolean;
  children: React.ReactNode;
}

export function PaymentField({
  label,
  error,
  focused,
  icon,
  helper,
  required,
  children
}: PaymentFieldProps) {
  return (
    <div className="space-y-1">
      <label className="flex items-center justify-between text-sm font-medium text-gray-700">
        <span>
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </span>
        {helper && (
          <span className="text-xs text-gray-500 font-normal flex items-center">
            <Info className="h-3 w-3 mr-1" />
            {helper}
          </span>
        )}
      </label>

      <div className="relative">
        {children}

        {icon && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
            {icon}
          </div>
        )}

        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="absolute -bottom-6 left-0 flex items-center text-xs text-red-600"
            >
              <AlertCircle className="h-3 w-3 mr-1" />
              {error}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

interface CardBrandIconProps {
  number: string;
}

export function CardBrandIcon({ number }: CardBrandIconProps) {
  const getCardType = (num: string) => {
    const cleanNum = num.replace(/\s/g, '');

    if (/^4/.test(cleanNum)) return 'visa';
    if (/^5[1-5]/.test(cleanNum)) return 'mastercard';
    if (/^3[47]/.test(cleanNum)) return 'amex';
    if (/^6(?:011|5)/.test(cleanNum)) return 'discover';

    return 'generic';
  };

  const cardType = getCardType(number);

  const icons = {
    visa: (
      <div className="text-blue-600 font-bold text-xs">VISA</div>
    ),
    mastercard: (
      <div className="flex">
        <div className="w-4 h-4 rounded-full bg-red-500 -mr-1.5" />
        <div className="w-4 h-4 rounded-full bg-yellow-500 opacity-80" />
      </div>
    ),
    amex: (
      <div className="text-blue-600 font-bold text-xs">AMEX</div>
    ),
    discover: (
      <div className="text-orange-600 font-bold text-xs">DISCOVER</div>
    ),
    generic: <CreditCard className="h-5 w-5 text-gray-400" />
  };

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={cardType}
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.8, opacity: 0 }}
        transition={{ duration: 0.2 }}
      >
        {icons[cardType]}
      </motion.div>
    </AnimatePresence>
  );
}

interface SecurityBadgesProps {
  className?: string;
}

export function SecurityBadges({ className }: SecurityBadgesProps) {
  const badges = [
    { icon: Lock, text: "SSL Encrypted", color: "text-green-600" },
    { icon: CheckCircle, text: "PCI Compliant", color: "text-blue-600" },
  ];

  return (
    <div className={cn("flex items-center justify-center space-x-6", className)}>
      {badges.map((badge, index) => (
        <motion.div
          key={badge.text}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: index * 0.1 }}
          className="flex items-center text-sm text-gray-600"
        >
          <badge.icon className={cn("mr-1.5 h-4 w-4", badge.color)} />
          <span>{badge.text}</span>
        </motion.div>
      ))}
    </div>
  );
}

interface ProcessingOverlayProps {
  isProcessing: boolean;
}

export function ProcessingOverlay({ isProcessing }: ProcessingOverlayProps) {
  return (
    <AnimatePresence>
      {isProcessing && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
        >
          <motion.div
            initial={{ scale: 0.9 }}
            animate={{ scale: 1 }}
            className="bg-white rounded-2xl p-8 shadow-2xl max-w-sm mx-4"
          >
            <div className="text-center">
              <div className="mb-4 inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-50">
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                >
                  <CreditCard className="h-8 w-8 text-blue-600" />
                </motion.div>
              </div>

              <h3 className="text-lg font-semibold mb-2">Processing Payment</h3>
              <p className="text-sm text-gray-600 mb-4">
                Please wait while we securely process your payment...
              </p>

              <div className="flex items-center justify-center space-x-2">
                {[0, 1, 2].map((index) => (
                  <motion.div
                    key={index}
                    animate={{
                      scale: [1, 1.2, 1],
                      opacity: [0.5, 1, 0.5],
                    }}
                    transition={{
                      duration: 1,
                      repeat: Infinity,
                      delay: index * 0.2,
                    }}
                    className="w-2 h-2 bg-blue-600 rounded-full"
                  />
                ))}
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export function formatCardNumber(value: string): string {
  const v = value.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
  const matches = v.match(/\d{4,16}/g);
  const match = (matches && matches[0]) || '';
  const parts = [];

  for (let i = 0, len = match.length; i < len; i += 4) {
    parts.push(match.substring(i, i + 4));
  }

  if (parts.length) {
    return parts.join(' ');
  } else {
    return value;
  }
}

export function formatExpiry(value: string): string {
  const v = value.replace(/\s+/g, '').replace(/[^0-9]/gi, '');

  if (v.length >= 2) {
    return v.slice(0, 2) + (v.length > 2 ? '/' + v.slice(2, 4) : '');
  }

  return v;
}

// Input mask component for better UX
interface MaskedInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  mask: 'card' | 'expiry' | 'cvc';
  onValueChange?: (value: string) => void;
}

export function MaskedInput({ mask, onValueChange, ...props }: MaskedInputProps) {
  const [value, setValue] = useState('');

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    let formattedValue = e.target.value;

    switch (mask) {
      case 'card':
        formattedValue = formatCardNumber(formattedValue);
        break;
      case 'expiry':
        formattedValue = formatExpiry(formattedValue);
        break;
      case 'cvc':
        formattedValue = formattedValue.replace(/\D/g, '').slice(0, 4);
        break;
    }

    setValue(formattedValue);
    onValueChange?.(formattedValue.replace(/\D/g, ''));
  };

  return (
    <input
      {...props}
      value={value}
      onChange={handleChange}
      className={cn(
        "w-full px-4 py-3 rounded-lg border transition-all duration-200",
        "focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent",
        "hover:border-gray-300",
        props.className
      )}
    />
  );
}