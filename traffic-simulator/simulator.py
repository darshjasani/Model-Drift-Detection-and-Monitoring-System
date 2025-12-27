"""Traffic Simulator - Generate Realistic Transaction Load with Drift"""

import os
import sys
import time
import asyncio
import httpx
import numpy as np
from datetime import datetime
import logging
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")
DEFAULT_RPS = int(os.getenv("DEFAULT_RPS", "10"))

class TrafficSimulator:
    """Simulate realistic transaction traffic with configurable drift"""
    
    def __init__(self, backend_url: str, rps: int = 10):
        """
        Initialize traffic simulator
        
        Args:
            backend_url: Backend API URL
            rps: Requests per second
        """
        self.backend_url = backend_url
        self.rps = rps
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.drift_config = {
            'enabled': False,
            'amount_shift': 0.0,
            'distance_shift': 0.0,
            'fraud_rate': 0.02
        }
        self.running = False
    
    def generate_transaction_features(self) -> dict:
        """Generate realistic transaction features with optional drift"""
        
        # Base fraud probability
        is_fraud = np.random.random() < self.drift_config['fraud_rate']
        
        # Apply drift multipliers
        amount_mult = 1.0 + self.drift_config['amount_shift']
        distance_mult = 1.0 + self.drift_config['distance_shift']
        
        if is_fraud:
            # Fraudulent transaction patterns
            features = {
                'amount': float(np.clip(np.random.gamma(3, 80, 1)[0] * amount_mult, 50, 10000)),
                'hour_of_day': int(np.random.randint(0, 24)),
                'day_of_week': int(np.random.randint(0, 7)),
                'distance_from_home_km': float(np.clip(np.abs(np.random.normal(45, 35)) * distance_mult, 0, 500)),
                'distance_from_last_txn_km': float(np.clip(np.abs(np.random.normal(30, 40)) * distance_mult, 0, 500)),
                'time_since_last_txn_mins': float(np.clip(np.abs(np.random.exponential(30)), 1, 1440)),
                'avg_amount_last_30d': float(np.clip(np.random.gamma(2, 40), 5, 3000)),
                'num_transactions_24h': int(np.clip(np.random.poisson(8), 0, 50)),
                'merchant_risk_score': float(np.clip(np.random.beta(5, 2), 0, 1)),
                'is_international': int(np.random.binomial(1, 0.35)),
                'card_present': int(np.random.binomial(1, 0.25)),
                'transaction_velocity': float(np.clip(np.random.gamma(3, 1), 0, 10))
            }
        else:
            # Legitimate transaction patterns
            features = {
                'amount': float(np.clip(np.random.gamma(2, 45, 1)[0] * amount_mult, 0.1, 5000)),
                'hour_of_day': int(np.random.choice(range(6, 23))),
                'day_of_week': int(np.random.randint(0, 7)),
                'distance_from_home_km': float(np.clip(np.abs(np.random.normal(8, 12)) * distance_mult, 0, 100)),
                'distance_from_last_txn_km': float(np.clip(np.abs(np.random.normal(5, 8)) * distance_mult, 0, 50)),
                'time_since_last_txn_mins': float(np.clip(np.abs(np.random.exponential(120)), 1, 1440)),
                'avg_amount_last_30d': float(np.clip(np.random.gamma(2, 40), 5, 3000)),
                'num_transactions_24h': int(np.clip(np.random.poisson(3), 0, 20)),
                'merchant_risk_score': float(np.clip(np.random.beta(2, 8), 0, 1)),
                'is_international': int(np.random.binomial(1, 0.05)),
                'card_present': int(np.random.binomial(1, 0.85)),
                'transaction_velocity': float(np.clip(np.random.gamma(1.5, 0.5), 0, 5))
            }
        
        return features, is_fraud
    
    async def send_transaction(self, client: httpx.AsyncClient) -> bool:
        """Send a single transaction to the backend"""
        try:
            # Generate transaction
            features, actual_fraud = self.generate_transaction_features()
            transaction_id = f"txn_{uuid.uuid4().hex[:12]}"
            
            # Send prediction request
            response = await client.post(
                f"{self.backend_url}/api/v1/predict",
                json={
                    "transaction_id": transaction_id,
                    "features": features,
                    "timestamp": datetime.utcnow().isoformat()
                },
                timeout=5.0
            )
            
            if response.status_code == 200:
                self.successful_requests += 1
                
                # Optionally send feedback (10% of the time, simulating delayed labels)
                if np.random.random() < 0.1:
                    await self.send_feedback(client, transaction_id, actual_fraud)
                
                return True
            else:
                self.failed_requests += 1
                logger.warning(f"Request failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.failed_requests += 1
            logger.error(f"Error sending transaction: {e}")
            return False
    
    async def send_feedback(self, client: httpx.AsyncClient, transaction_id: str, actual_label: int):
        """Send ground truth feedback"""
        try:
            await client.post(
                f"{self.backend_url}/api/v1/feedback",
                json={
                    "transaction_id": transaction_id,
                    "actual_label": actual_label,
                    "label_source": "simulator",
                    "confidence": "high"
                },
                timeout=5.0
            )
        except Exception as e:
            logger.debug(f"Error sending feedback: {e}")
    
    async def run_traffic_loop(self):
        """Main traffic generation loop"""
        logger.info(f"Starting traffic generation: {self.rps} req/sec")
        
        interval = 1.0 / self.rps  # Time between requests
        
        async with httpx.AsyncClient() as client:
            while self.running:
                try:
                    start_time = time.time()
                    
                    # Send transaction
                    await self.send_transaction(client)
                    self.total_requests += 1
                    
                    # Log stats periodically
                    if self.total_requests % 100 == 0:
                        success_rate = (self.successful_requests / self.total_requests * 100) if self.total_requests > 0 else 0
                        logger.info(
                            f"Traffic stats: Total={self.total_requests}, "
                            f"Success={self.successful_requests}, "
                            f"Failed={self.failed_requests}, "
                            f"Success Rate={success_rate:.1f}%, "
                            f"Drift={'ON' if self.drift_config['enabled'] else 'OFF'}"
                        )
                    
                    # Maintain rate
                    elapsed = time.time() - start_time
                    sleep_time = max(0, interval - elapsed)
                    await asyncio.sleep(sleep_time)
                    
                except Exception as e:
                    logger.error(f"Error in traffic loop: {e}")
                    await asyncio.sleep(1)
    
    def enable_drift(self, amount_shift: float = 0.3, distance_shift: float = 0.5, fraud_rate: float = 0.05):
        """
        Enable drift in generated data
        
        Args:
            amount_shift: Multiplier for transaction amounts (0.3 = 30% increase)
            distance_shift: Multiplier for distances
            fraud_rate: New fraud rate
        """
        self.drift_config = {
            'enabled': True,
            'amount_shift': amount_shift,
            'distance_shift': distance_shift,
            'fraud_rate': fraud_rate
        }
        logger.info(f"Drift enabled: amount_shift={amount_shift}, "
                   f"distance_shift={distance_shift}, fraud_rate={fraud_rate}")
    
    def disable_drift(self):
        """Disable drift"""
        self.drift_config = {
            'enabled': False,
            'amount_shift': 0.0,
            'distance_shift': 0.0,
            'fraud_rate': 0.02
        }
        logger.info("Drift disabled")
    
    async def start(self):
        """Start the simulator"""
        logger.info("=" * 60)
        logger.info("ML Drift Detection - Traffic Simulator")
        logger.info("=" * 60)
        logger.info(f"Backend URL: {self.backend_url}")
        logger.info(f"Target RPS: {self.rps}")
        logger.info("=" * 60)
        
        # Wait for backend to be ready
        logger.info("Waiting for backend to be ready...")
        await self.wait_for_backend()
        
        logger.info("Starting traffic generation...")
        self.running = True
        
        # Run traffic loop
        await self.run_traffic_loop()
    
    async def wait_for_backend(self, max_retries: int = 30):
        """Wait for backend to be available"""
        async with httpx.AsyncClient() as client:
            for i in range(max_retries):
                try:
                    response = await client.get(f"{self.backend_url}/health", timeout=5.0)
                    if response.status_code == 200:
                        logger.info("✓ Backend is ready!")
                        return
                except Exception as e:
                    logger.info(f"Waiting for backend... ({i+1}/{max_retries})")
                    await asyncio.sleep(2)
        
        logger.warning("Backend not ready after max retries, starting anyway...")
    
    def stop(self):
        """Stop the simulator"""
        self.running = False
        logger.info("Simulator stopped")


async def main():
    """Main entry point"""
    simulator = TrafficSimulator(
        backend_url=BACKEND_URL,
        rps=DEFAULT_RPS
    )
    
    try:
        await simulator.start()
    except KeyboardInterrupt:
        logger.info("Simulator stopped by user")
        simulator.stop()


if __name__ == "__main__":
    asyncio.run(main())

