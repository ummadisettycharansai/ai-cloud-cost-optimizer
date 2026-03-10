# AI Cloud Cost Optimizer (FinOps SaaS Platform)

![FinOps AI](https://img.shields.io/badge/FinOps-Platform-blueviolet?style=for-the-badge&logo=cloud)
![Python Backend](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![React Frontend](https://img.shields.io/badge/React_Admin-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![Streaming](https://img.shields.io/badge/Kafka-231F20?style=for-the-badge&logo=apachekafka&logoColor=white)

An enterprise-grade, event-driven FinOps platform designed to identify, forecast, and autonomously remediate cloud infrastructure waste across AWS, Azure, and Google Cloud Platform (GCP).

---

## 🌐 Live Demo

Frontend dashboard deployed on Vercel:
[https://ai-cloud-cost-optimizer.vercel.app](https://ai-cloud-cost-optimizer.vercel.app)

*Note: The backend API must also be deployed and accessible for full functionality.*

---

## 🚀 Project Overview

Modern cloud infrastructure often incurs massive hidden costs due to idle resources, over-provisioning, and forgotten storage volumes. The **AI Cloud Cost Optimizer** solves this by uniting real-world billing APIs with AI-driven anomaly detection and **Cost Autopilot**, a system capable of executing automated remediation (e.g., shutting down idle EC2s or scaling down VMs) subject to strict safety policies.

**Key Value Propositions:**
1. **Multi-Tenant:** Supports multiple sub-organizations, projects, and Role-Based Access Control (Admin, Finance, Viewer).
2. **Unified Billing:** Connects securely to AWS CE, Azure Cost Management, and GCP Billing.
3. **Event-Driven:** Uses Apache Kafka for real-time cost event streaming.
4. **Autonomous:** AI Cost Autopilot executes safe resource optimization without human intervention.
5. **Production-Ready:** Containerized with Docker, deployable via Kubernetes, monitored via Prometheus/Grafana.

---

## 🏗️ Architecture

![Architecture](docs/architecture.png)

### Deployment Architecture
- **React Dashboard:** Vercel
- **FastAPI Backend:** Cloud server (Render / AWS / Railway)
- **Data Persistence:** Managed database (PostgreSQL)
- **Event Streaming:** Kafka Event Pipeline

### System Components
The system leverages a microservices-inspired design:
- **React Frontend:** Communicates via REST to FastAPI.
- **FastAPI Core:** Handles Budgets, Org RBAC, and Authentication.
- **Data Persistence:** Uses PostgreSQL and Redis object caching.
- **Kafka Streaming:** Produces cost ingestion messages to topics.
- **Python Consumers:** Processes anomalies async and trains Poly-Regression forecasting models.

---

## ✨ Features

*   **Multi-Cloud Integration:** Connect AWS, Azure, and GCP accounts securely via encrypted credential storage.
*   **Budget Engine:** Track organizational spend vs allocations, with real-time alerting thresholds.
*   **AI Cost Forecasting:** Uses polynomial regression to predict trailing 30-day spend signatures into the future.
*   **Anomaly Detection:** Z-Score based isolation mechanisms detect sudden cost spikes in billing data within hours.
*   **Recommendation Matrix:** Scans inventory to suggest Spot Instance migrations, S3 Glacier tiering, disk deletions, and rightsizing.
*   **Cost Autopilot:** An autonomous agent that reads recommendations and physically executes them via Cloud SDKs if allowed.

---

## 🛠️ Technology Stack

*   **Backend:** Python 3.12+, FastAPI, SQLAlchemy, Alembic, Celery.
*   **Frontend:** React 18, Vite, TypeScript, TailwindCSS, Recharts.
*   **Data & Streaming:** PostgreSQL 15, Redis 7, Apache Kafka & Zookeeper.
*   **DevOps & Observability:** Docker Compose, Kubernetes, Prometheus, Jaeger.
*   **Testing:** Pytest & Playwright (High End-to-End coverage achieved).

---

## 💻 Installation Guide (Local Docker)

The easiest way to run the entire distributed FinOps stack is via Docker Compose.

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/yourusername/ai-cloud-cost-optimizer.git
    cd ai-cloud-cost-optimizer
    ```
2.  **Environment Variables:**
    ```bash
    cp backend/.env.example backend/.env
    # The system will auto-generate encryption keys for DB storage
    ```
3.  **Boot the Stack:**
    ```bash
    docker-compose up --build
    ```
4.  **Access the applications:**
    *   React Dashboard: `http://localhost:5173`
    *   FastAPI Swagger Docs: `http://localhost:8000/docs`

---

## 🚢 Deployment Guide (Kubernetes)

The project includes YAML manifests for deployment to EKS, AKS, or GKE.

1.  **Configure Secrets:**
    Update `kubernetes/config-secrets.yaml` with your base64 encoded DB passwords and JWT hashes.
2.  **Apply Manifests:**
    ```bash
    kubectl apply -f kubernetes/
    ```
3.  **Check Services:**
    ```bash
    kubectl get pods -l app=finops-backend
    kubectl get svc finops-ingress
    ```

---

## 📷 Screenshots

| Dashboard Overview | Cost Autopilot UI |
| :---: | :---: |
| ![Dashboard Overview](docs/screenshots/dashboard.png) | ![Cost Autopilot](docs/screenshots/autopilot.png) |

| AI Forecasts | Budget Configurator | Cloud Connections Hub |
| :---: | :---: | :---: |
| ![AI Forecasts](docs/screenshots/forecast.png) | ![Budget Configurator](docs/screenshots/budgets.png) | ![Connections Hub](docs/screenshots/cloud-connections.png) |

---

## 🔄 Demo Workflow

1. **Organization Creation:** Sign up an admin. Creates `FinOps Alpha` org.
2. **Cloud Connect:** Navigate to settings. Add mock AWS credentials (saved via Fernet).
3. **Trigger Pipeline:** Run `verify_full_pipeline.py` which pushes JSON payloads into Kafka.
4. **View Budgets:** Open `http://localhost:5173/budgets`. Observe total vs projected spend.
5. **Autopilot Enablement:** Set Safety Policy to 'High'. AI will execute Right-Sizing logic on mock EC2 responses. Watch the Notification bell ping.

---

## 🛠️ Engineering Highlights

- **JWT + RBAC Middleware:** Implemented secure route dependencies protecting Org-level separation.
- **Fernet Symmetric Security:** AWS Account Secret Access keys are never plaintext in Postgres.
- **Decoupled Event Streaming:** `celery_worker` drops heavy polling cycles, pushing data to `kafka` for down-stream consumers to handle Isolation Forest Anomaly Detection independent of API latency.

---

## ☁️ GitHub Repository Setup

To host this project on GitHub for team collaboration, follow these push instructions:

1. Create a new repository on GitHub named **`ai-cloud-cost-optimizer`**.
2. Add the remote origin:
   ```bash
   git remote add origin https://github.com/<username>/ai-cloud-cost-optimizer.git
   ```
3. Push the project:
   ```bash
   git branch -M main
   git push -u origin main
   ```

---

## 🤝 Team Collaboration

We welcome team collaboration! Follow these steps to get started:

### Adding Collaborators
Repository administrators should navigate to **Repository Settings → Collaborators → Add People**. 
Recommended roles:
- **Admin**: For Senior Engineers / DevOps.
- **Write**: For standard developers merging Pull Requests.
- **Read**: For viewers and stakeholders.

### Branch Workflow
Please utilize feature branching and Pull Requests for any modifications:

1. Create a branch:
   ```bash
   git checkout -b feature-autopilot-ui
   ```
2. Make your commits, then push:
   ```bash
   git push origin feature-autopilot-ui
   ```
3. Open a Pull Request on GitHub. Ensure CI/CD GitHub Actions pass before requesting a review.
