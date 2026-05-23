import argparse
import logging
import sys

from backend.crons.predict_markets.helpers import (
    predict_all_configs,
    predict_with_config,
)


def main(argv: list[str] | None = None) -> bool:
    parser = argparse.ArgumentParser(
        prog="predict_markets",
        description="Run LLM market predictions. With no args, runs every active config across every active market.",
    )

    parser.add_argument(
        "--config",
        dest="config_name",
        help="Run only the named llm_config (matches llm_config.name). Required when --market-id is set.",
    )
    parser.add_argument(
        "--market-id",
        dest="market_id",
        help="Restrict the run to a single market_id (e.g. mkt_<uuid>). Requires --config.",
    )

    args = parser.parse_args(argv)

    if args.market_id and not args.config_name:
        parser.error("--market-id requires --config")

    if args.config_name:
        return predict_with_config(args.config_name, args.market_id)

    return predict_all_configs()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s"
    )
    sys.exit(0 if main() else 1)
