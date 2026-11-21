import logging

# Runtime platforms capture stderr; do not write inside the deployment bundle.
logging.basicConfig(
    format="[%(asctime)s] %(name)s %(levelname)s: %(message)s",
    level=logging.INFO,
)
