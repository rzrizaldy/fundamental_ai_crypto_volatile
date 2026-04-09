Programming Assignment: Building a Real-Time Crypto AI Service
You’ll work in teams of five to transform one of your individual volatility detection models into a real-time AI service. Across four weeks, your team will design, build, deploy, and monitor a system that can:

Stream live data from Coinbase (via Kafka)
Process and predict in real time using FastAPI
Track models with MLflow
Monitor performance using Prometheus, Grafana, and Evidently
Assignment Overview
Your deliverables will combine engineering depth with operational excellence—just as you’d expect in an enterprise AI environment.

Weekly Plan
Week 4 – System Setup & API Thin Slice
Goal: Build your first working system prototype in replay mode (not live yet).

Tasks:
• Choose your base or composite model.
• Draw a simple system diagram (ingestor → features → API → monitoring).
• Create /health, /predict, /version, and /metrics endpoints in FastAPI.
• Launch Kafka (KRaft) and MLflow using Docker Compose.
• Replay a 10-minute dataset to test your pipeline.
• Write two docs: team_charter.md (roles) and selection_rationale.md (model choice).

Deliverables:
• docker-compose.yaml, Dockerfiles, and architecture diagram
• Working /predict endpoint (with sample curl)
• Team charter + selection rationale