import logging
import uuid
from typing import Optional
from datetime import datetime

from apps.broker_connector.alpaca_client import AlpacaClient

logger = logging.getLogger(__name__)

class IBRoutingBroker:
    """
    Wrapper around the master execution client (Alpaca API) designed to handle 
    Institutional Introducing Broker (IB) tagging.
    
    By tagging our massive block orders with a specific IB routing prefix, 
    we capture volume rebates and lower our aggregate cost-basis per share.
    """
    
    def __init__(self, ib_tag: str = "PFRM_IB"):
        """
        Initialize the routing wrapper.
        
        Args:
            ib_tag: The institutional prefix agreed upon with the clearing firm.
        """
        self.client = AlpacaClient()
        self.ib_tag = ib_tag
        
    def generate_routing_tag(self, strategy_name: str) -> str:
        """
        Generate a unique client_order_id compliant with Alpaca's 48-char limit,
        while embedding our IB tag and strategy source.
        
        Format: {IB_TAG}-{STRATEGY[:10]}-{UUID4[:8]}
        """
        strat_short = strategy_name.replace(" ", "")[:10].upper()
        unique_id = str(uuid.uuid4())[:8]
        tag = f"{self.ib_tag}-{strat_short}-{unique_id}"
        return tag[:48] # Enforce absolute length limit

    def submit_block_order(
        self,
        strategy_name: str,
        symbol: str,
        qty: float,
        side: str,
        order_type: str = "market",
        time_in_force: str = "day",
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
    ) -> dict:
        """
        Formats the Institutional tag and delegates to the underlying broker client.
        """
        # Generate the tagged client order ID for volume rebates
        routing_tag = self.generate_routing_tag(strategy_name)
        
        logger.info(f"Routing Block Order via IB Gateway: {routing_tag} ({qty} shs {symbol})")
        
        return self.client.submit_order(
            symbol=symbol,
            qty=qty,
            side=side,
            order_type=order_type,
            time_in_force=time_in_force,
            limit_price=limit_price,
            stop_price=stop_price,
            client_order_id=routing_tag
        )
