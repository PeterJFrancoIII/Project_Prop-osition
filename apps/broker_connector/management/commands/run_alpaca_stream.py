import logging
import asyncio
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.conf import settings

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Run the Alpaca WebSocket stream to listen for live trade execution updates."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting Alpaca WebSocket Stream..."))
        try:
            from alpaca_trade_api.stream import Stream
        except ImportError:
            self.stdout.write(self.style.ERROR("alpaca-trade-api not installed. Run: pip install alpaca-trade-api"))
            return

        api_key = settings.BROKER_ALPACA_API_KEY
        secret_key = settings.BROKER_ALPACA_SECRET_KEY
        base_url = settings.BROKER_ALPACA_BASE_URL
        
        # Determine if paper or live
        data_feed = 'iex' if 'paper' in base_url else 'sip'

        # Initialize stream
        stream = Stream(api_key, secret_key, base_url=base_url, data_feed=data_feed)

        async def trade_update_handler(data):
            """Callback for trade updates from Alpaca."""
            event = getattr(data, 'event', 'unknown')
            order = getattr(data, 'order', None)
            
            if not order:
                return

            order_id = getattr(order, 'id', None)
            if not order_id:
                return
                
            logger.info(f"Trade Update: {event} for order {order_id}")
            
            from apps.execution_engine.models import Trade
            from apps.execution_engine.executor import _update_cost_basis
            from apps.execution_engine.notifications import DiscordNotifier
            
            try:
                # Find the corresponding trade in our tracking DB
                trade = Trade.objects.filter(broker_order_id=order_id).first()
                if not trade:
                    # Trade might have been placed manually outside the system
                    return

                # Handle fills
                if event in ('fill', 'partial_fill'):
                    trade.status = 'filled' if event == 'fill' else 'partial_fill'
                    
                    filled_avg_price = getattr(order, 'filled_avg_price', None)
                    if filled_avg_price:
                        trade.fill_price = Decimal(str(filled_avg_price))
                        
                    filled_qty = getattr(order, 'filled_qty', None)
                    if filled_qty:
                        trade.quantity = Decimal(str(filled_qty))

                    # Re-calculate P&L on the new truth using cost basis
                    _update_cost_basis(trade)
                    trade.save()
                    
                    if event == 'fill':
                        DiscordNotifier().send_trade_alert(trade)
                        
                # Handle interruptions
                elif event in ('rejected', 'canceled', 'suspended'):
                    trade.status = event
                    trade.save()
                    DiscordNotifier().send_system_alert(
                        title=f"Order {event.title()}: {trade.symbol}",
                        message=f"Broker {event} order {order_id}",
                        level="WARNING"
                    )
            except Exception as e:
                logger.error(f"Error handling trade update for {order_id}: {e}")

        # Subscribe and run infinite loop
        try:
            self.stdout.write("Subscribing to trade_updates...")
            stream.subscribe_trade_updates(trade_update_handler)
            stream.run()
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\nShutting down stream listener..."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Stream error: {e}"))
