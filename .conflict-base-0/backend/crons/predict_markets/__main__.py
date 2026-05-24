import logging
import sys

from backend.crons.predict_markets.main import main

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s"
)
sys.exit(0 if main() else 1)
