# 🚀 Quick Start Guide

## Prerequisites
- Docker and Docker Compose installed
- 8GB RAM minimum
- 10GB free disk space

## Start the System (One Command!)

```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

This script will:
1. Build all Docker images
2. Generate synthetic training data
3. Train the XGBoost model
4. Start all services (database, backend, frontend, workers)
5. Begin traffic simulation

**Expected time**: 5-10 minutes on first run

## Access the Dashboard

Once setup is complete:

1. **Open your browser**: http://localhost:3000
2. **Wait 30 seconds** for initial predictions
3. **Explore the tabs**:
   - Overview: System health and model info
   - Drift Detection: Feature drift analysis
   - Performance: Metrics over time

## What You'll See

### Immediately
- ✅ System online indicator
- ✅ Model information (version, training date)
- ✅ Live prediction counter

### After 30-60 seconds
- ✅ First metrics appearing
- ✅ Drift scores calculating
- ✅ Charts populating

### After 5 minutes
- ✅ Drift detection working (some features will show drift)
- ✅ Performance trends visible
- ✅ Alerts appearing

## Common Commands

```bash
# View logs
docker-compose logs -f backend

# Restart services
docker-compose restart

# Stop everything
docker-compose down

# Retrain model
./scripts/train_model.sh

# Check service status
docker-compose ps
```

## Troubleshooting

### "Database connection failed"
```bash
# Restart database
docker-compose restart postgres
sleep 5
docker-compose restart backend
```

### "Model not found"
```bash
# Train the model
docker-compose run --rm backend python -m app.ml.train
```

### "Frontend not loading"
```bash
# Check if frontend is running
docker-compose ps frontend

# Restart frontend
docker-compose restart frontend
```

### "No data in dashboard"
```bash
# Check if traffic simulator is running
docker-compose logs traffic-simulator

# Restart simulator
docker-compose restart traffic-simulator
```

## Verify Everything Works

1. **Backend Health**: `curl http://localhost:8000/health`
   - Should return `{"status": "healthy", ...}`

2. **Make a Prediction**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/predict \
     -H "Content-Type: application/json" \
     -d '{
       "transaction_id": "test_001",
       "features": {
         "amount": 150.0,
         "hour_of_day": 14,
         "day_of_week": 3,
         "distance_from_home_km": 5.2,
         "distance_from_last_txn_km": 8.1,
         "time_since_last_txn_mins": 45.0,
         "avg_amount_last_30d": 120.0,
         "num_transactions_24h": 3,
         "merchant_risk_score": 0.15,
         "is_international": 0,
         "card_present": 1,
         "transaction_velocity": 1.2
       }
     }'
   ```

3. **Get Drift Report**:
   ```bash
   curl http://localhost:8000/api/v1/monitoring/drift/latest?hours=1
   ```

## Demo for Recruiters

**5-Minute Walkthrough:**

1. Show the running dashboard (localhost:3000)
2. Point out the live prediction counter
3. Navigate to "Drift Detection" tab
4. Show a feature with drift (PSI > 0.25)
5. Explain: "This catches model degradation before it impacts business"

**Key Talking Points:**
- Real ML model (not hardcoded)
- Live drift detection (PSI, KS tests)
- Production-ready architecture (FastAPI, React, Docker)
- Actionable insights (feature-level analysis)

## Need Help?

Check the full README.md for:
- Detailed architecture
- Configuration options
- Technical deep-dive
- Troubleshooting guide

---

**Now go show this to recruiters! 🎯**

