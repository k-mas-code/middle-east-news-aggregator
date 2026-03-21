"""
Command-line interface for Middle East News Aggregator.

Provides CLI commands for running the collection pipeline.
"""

import sys
import logging
from datetime import datetime
from typing import Optional

from middle_east_aggregator.pipeline import NewsPipeline


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('collection.log', mode='a')
    ]
)

logger = logging.getLogger(__name__)


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def print_summary(result: dict) -> None:
    """
    Print collection summary.

    Args:
        result: Pipeline execution result dictionary
    """
    print("\n" + "=" * 60)
    print("COLLECTION SUMMARY")
    print("=" * 60)

    status = result.get('status', 'unknown')
    print(f"Status: {status.upper()}")

    if status == 'success':
        print(f"✓ Articles collected: {result.get('articles_collected', 0)}")
        print(f"✓ Articles filtered: {result.get('articles_filtered', 0)}")
        print(f"✓ Clusters created: {result.get('clusters_created', 0)}")
        print(f"✓ Reports generated: {result.get('reports_generated', 0)}")

        duration = result.get('duration_seconds', 0)
        print(f"✓ Duration: {format_duration(duration)}")

        # Calculate filtering rate
        collected = result.get('articles_collected', 0)
        filtered = result.get('articles_filtered', 0)
        if collected > 0:
            filter_rate = (filtered / collected) * 100
            print(f"✓ Filter rate: {filter_rate:.1f}%")

    elif status == 'error':
        error_msg = result.get('error', 'Unknown error')
        print(f"✗ Error: {error_msg}")

        # Print partial results if available
        if result.get('articles_collected', 0) > 0:
            print(f"  Partial - Articles collected: {result.get('articles_collected', 0)}")
            print(f"  Partial - Articles filtered: {result.get('articles_filtered', 0)}")

    print("=" * 60 + "\n")


def collect() -> int:
    """
    Run the news collection pipeline.

    Returns:
        Exit code (0 for success, 1 for error)

    Validates: Requirements 1.2, 1.6, 7.3, 7.4
    """
    logger.info("=" * 60)
    logger.info("Starting news collection pipeline")
    logger.info(f"Timestamp: {datetime.utcnow().isoformat()}Z")
    logger.info("=" * 60)

    try:
        # Run the pipeline
        pipeline = NewsPipeline()
        result = pipeline.run()

        # Log and print summary
        logger.info(f"Pipeline completed with status: {result.get('status')}")
        print_summary(result)

        # Return appropriate exit code
        if result.get('status') == 'success':
            logger.info("Collection completed successfully")
            return 0
        else:
            logger.error(f"Collection failed: {result.get('error', 'Unknown error')}")
            return 1

    except KeyboardInterrupt:
        logger.warning("Collection interrupted by user")
        print("\n⚠ Collection interrupted by user")
        return 130  # Standard exit code for SIGINT

    except Exception as e:
        logger.exception("Unexpected error during collection")
        print(f"\n✗ Unexpected error: {e}")
        return 1


def main() -> int:
    """
    Main CLI entry point.

    Returns:
        Exit code
    """
    if len(sys.argv) < 2:
        print("Usage: python -m middle_east_aggregator.cli <command>")
        print("\nCommands:")
        print("  collect    Run the news collection pipeline")
        return 1

    command = sys.argv[1]

    if command == "collect":
        return collect()
    else:
        print(f"Unknown command: {command}")
        print("\nAvailable commands:")
        print("  collect    Run the news collection pipeline")
        return 1


if __name__ == "__main__":
    sys.exit(main())
