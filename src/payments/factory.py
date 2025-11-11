# src/payments/factory.py
from typing import Dict, Any
from .base import BasePaymentProvider, PaymentProvider
from .providers.razorpay_provider import RazorpayProvider
from .providers.stripe_provider import StripeProvider

class PaymentProviderFactory:
    """Factory for creating payment provider instances"""
    
    _providers = {
        PaymentProvider.RAZORPAY: RazorpayProvider,
        PaymentProvider.STRIPE: StripeProvider
    }
    
    @classmethod
    def create_provider(
        cls,
        provider: PaymentProvider,
        config: Dict[str, Any]
    ) -> BasePaymentProvider:
        """
        Create a payment provider instance
        
        Args:
            provider: Provider type (razorpay/stripe)
            config: Provider-specific configuration
        
        Returns:
            BasePaymentProvider instance
        
        Raises:
            ValueError: If provider not supported
        """
        provider_class = cls._providers.get(provider)
        
        if not provider_class:
            raise ValueError(f"Unsupported payment provider: {provider}")
        
        return provider_class(config)
    
    @classmethod
    def get_supported_providers(cls):
        """Get list of supported providers"""
        return list(cls._providers.keys())