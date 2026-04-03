"""WhatsApp bot handlers."""
from whatsapp.handlers import start
from whatsapp.handlers import balance
from whatsapp.handlers import deposit
from whatsapp.handlers import bundles
from whatsapp.handlers import history
from whatsapp.handlers import referral
from whatsapp.handlers import help

# Export handlers
start_handler = start.start_handler
balance_handler = balance.balance_handler
history_handler = history.history_handler
referral_handler = referral.referral_handler
help_handler = help.help_handler

# Create handler modules for easier import
deposit_handler = type('DepositHandler', (), {
    'start': deposit.start,
    'handle_amount': deposit.handle_amount,
    'handle_phone': deposit.handle_phone,
    'handle_otp': deposit.handle_otp
})()

bundles_handler = type('BundlesHandler', (), {
    'start': bundles.start,
    'handle_network': bundles.handle_network,
    'handle_bundle': bundles.handle_bundle,
    'handle_phone': bundles.handle_phone
})()

