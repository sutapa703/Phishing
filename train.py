"""Train from a labeled CSV or the configured MongoDB database."""
import argparse
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / '.env')

from src.pipeline.train_pipeline import TrainingPipeline
from src.constant import MODEL_PATH


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', help='Labeled CSV file or directory of CSV files; otherwise use MongoDB.')
    args = parser.parse_args()
    try:
        score = TrainingPipeline(args.data).run_pipeline()
    except Exception as error:
        parser.exit(1, f'Training failed: {error}\n')
    print(f'Training completed. Held-out accuracy: {score:.4f}. Model: {MODEL_PATH}')


if __name__ == '__main__':
    main()
