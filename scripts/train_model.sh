#!/bin/bash

# Train or retrain the ML model

echo "Training ML Model..."
docker-compose run --rm backend python -m app.ml.train
echo "Model training complete!"

