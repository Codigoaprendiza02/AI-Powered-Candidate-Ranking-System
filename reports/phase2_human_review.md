# Phase 2 Human Review: Hard Filters & Honeypot Audit

This document summarizes the sampled candidates for manual audit, verifying the correctness of Layer 1 hard filters and honeypot detection rules.

## Section 1: Flagged Honeypot Audit (20 Samples)

These candidates are flagged as honeypots based on impossible profile properties:

### 1. Candidate: `CAND_0001610`
- **Name**: Aryan Banerjee
- **Current Title**: Machine Learning Engineer
- **Years of Experience**: 3.0
- **Total Career Duration (Months)**: 61
- **Anomalous Heuristics**:
  - Skill overflow: 12 skill(s) exceed YoE (e.g., Speech Recognition: 50 months against 3.0 YoE)
  - Career duration overflow: sum of jobs = 61 months against 3.0 YoE

### 2. Candidate: `CAND_0003582`
- **Name**: Ishaan Tiwari
- **Current Title**: Mobile Developer
- **Years of Experience**: 8.2
- **Total Career Duration (Months)**: 98
- **Anomalous Heuristics**:
  - Expert with 0 months: MLflow, Photoshop, Content Writing

### 3. Candidate: `CAND_0007353`
- **Name**: Aarav Subramanian
- **Current Title**: Frontend Engineer
- **Years of Experience**: 9.9
- **Total Career Duration (Months)**: 251
- **Anomalous Heuristics**:
  - Career duration overflow: sum of jobs = 251 months against 9.9 YoE

### 4. Candidate: `CAND_0008960`
- **Name**: Meera Naidu
- **Current Title**: Graphic Designer
- **Years of Experience**: 10.3
- **Total Career Duration (Months)**: 271
- **Anomalous Heuristics**:
  - Career duration overflow: sum of jobs = 271 months against 10.3 YoE

### 5. Candidate: `CAND_0010294`
- **Name**: Reyansh Nair
- **Current Title**: .NET Developer
- **Years of Experience**: 8.0
- **Total Career Duration (Months)**: 220
- **Anomalous Heuristics**:
  - Career duration overflow: sum of jobs = 220 months against 8.0 YoE

### 6. Candidate: `CAND_0016000`
- **Name**: Aarav Bansal
- **Current Title**: Full Stack Developer
- **Years of Experience**: 2.0
- **Total Career Duration (Months)**: 24
- **Anomalous Heuristics**:
  - Expert with 0 months: TypeScript, Go, Docker, Hadoop, Photoshop

### 7. Candidate: `CAND_0018515`
- **Name**: Aarohi Dalal
- **Current Title**: Marketing Manager
- **Years of Experience**: 8.5
- **Total Career Duration (Months)**: 211
- **Anomalous Heuristics**:
  - Career duration overflow: sum of jobs = 211 months against 8.5 YoE

### 8. Candidate: `CAND_0019480`
- **Name**: Priya Bhatia
- **Current Title**: NLP Engineer
- **Years of Experience**: 2.8
- **Total Career Duration (Months)**: 87
- **Anomalous Heuristics**:
  - Skill overflow: 5 skill(s) exceed YoE (e.g., LLMs: 82 months against 2.8 YoE)
  - Career duration overflow: sum of jobs = 87 months against 2.8 YoE

### 9. Candidate: `CAND_0033817`
- **Name**: Yash Bansal
- **Current Title**: HR Manager
- **Years of Experience**: 13.3
- **Total Career Duration (Months)**: 157
- **Anomalous Heuristics**:
  - Expert with 0 months: JavaScript, BigQuery, Six Sigma, gRPC

### 10. Candidate: `CAND_0033972`
- **Name**: Nisha Gupta
- **Current Title**: QA Engineer
- **Years of Experience**: 6.0
- **Total Career Duration (Months)**: 71
- **Anomalous Heuristics**:
  - Expert with 0 months: Airflow, OpenCV, Figma

### 11. Candidate: `CAND_0035104`
- **Name**: Ayaan Chopra
- **Current Title**: Software Engineer
- **Years of Experience**: 5.5
- **Total Career Duration (Months)**: 162
- **Anomalous Heuristics**:
  - Career duration overflow: sum of jobs = 162 months against 5.5 YoE

### 12. Candidate: `CAND_0036839`
- **Name**: Tanvi Saxena
- **Current Title**: Operations Manager
- **Years of Experience**: 8.1
- **Total Career Duration (Months)**: 96
- **Anomalous Heuristics**:
  - Expert with 0 months: SAP, GCP, Rust

### 13. Candidate: `CAND_0037000`
- **Name**: Nikhil Mittal
- **Current Title**: Search Engineer
- **Years of Experience**: 2.7
- **Total Career Duration (Months)**: 75
- **Anomalous Heuristics**:
  - Skill overflow: 11 skill(s) exceed YoE (e.g., Embeddings: 39 months against 2.7 YoE)
  - Career duration overflow: sum of jobs = 75 months against 2.7 YoE

### 14. Candidate: `CAND_0037539`
- **Name**: Aryan Subramanian
- **Current Title**: Project Manager
- **Years of Experience**: 4.9
- **Total Career Duration (Months)**: 115
- **Anomalous Heuristics**:
  - Career duration overflow: sum of jobs = 115 months against 4.9 YoE

### 15. Candidate: `CAND_0039521`
- **Name**: Kiara Krishnan
- **Current Title**: Search Engineer
- **Years of Experience**: 3.0
- **Total Career Duration (Months)**: 59
- **Anomalous Heuristics**:
  - Skill overflow: 7 skill(s) exceed YoE (e.g., Hugging Face Transformers: 68 months against 3.0 YoE)
  - Career duration overflow: sum of jobs = 59 months against 3.0 YoE

### 16. Candidate: `CAND_0040075`
- **Name**: Aditya Singh
- **Current Title**: Marketing Manager
- **Years of Experience**: 15.0
- **Total Career Duration (Months)**: 365
- **Anomalous Heuristics**:
  - Career duration overflow: sum of jobs = 365 months against 15.0 YoE

### 17. Candidate: `CAND_0040853`
- **Name**: Manish Hegde
- **Current Title**: Operations Manager
- **Years of Experience**: 1.1
- **Total Career Duration (Months)**: 61
- **Anomalous Heuristics**:
  - Skill overflow: 1 skill(s) exceed YoE (e.g., Project Management: 23 months against 1.1 YoE)
  - Career duration overflow: sum of jobs = 61 months against 1.1 YoE

### 18. Candidate: `CAND_0042245`
- **Name**: Siya Trivedi
- **Current Title**: Business Analyst
- **Years of Experience**: 7.9
- **Total Career Duration (Months)**: 93
- **Anomalous Heuristics**:
  - Expert with 0 months: Databricks, BentoML, Vue.js

### 19. Candidate: `CAND_0042453`
- **Name**: Sanjay Bhatia
- **Current Title**: Marketing Manager
- **Years of Experience**: 4.2
- **Total Career Duration (Months)**: 98
- **Anomalous Heuristics**:
  - Career duration overflow: sum of jobs = 98 months against 4.2 YoE

### 20. Candidate: `CAND_0043721`
- **Name**: Ela Patel
- **Current Title**: Sales Executive
- **Years of Experience**: 4.5
- **Total Career Duration (Months)**: 108
- **Anomalous Heuristics**:
  - Career duration overflow: sum of jobs = 108 months against 4.5 YoE

---

## Section 2: Excluded Candidates Audit

Samples for each hard filter exclusion type to confirm that valid matches are not over-excluded:

### Exclusion Type: `Title Chaser`

#### 1. `CAND_0001085` — Senior Software Engineer
- **Industry**: Manufacturing | **Company**: Acme Corp | **YoE**: 5.5
- **Skills**: Elasticsearch, Weaviate, Kafka, Learning to Rank, Information Retrieval, Feature Engineering, OpenCV, TTS, YOLO, Weights & Biases
- **Snippet**: Software / data professional with 5.5 years of experience building data pipelines, backend systems, and analytics infrastructure. I've been the engineer who makes ML possible by getting the data pipel...

#### 2. `CAND_0007153` — Senior Data Engineer
- **Industry**: Conglomerate | **Company**: Wayne Enterprises | **YoE**: 4.3
- **Skills**: Forecasting, Computer Vision, Image Classification, Apache Flink, Semantic Search, Snowflake, Project Management, FastAPI, Sentence Transformers, Spark
- **Snippet**: Software / data professional with 4.3 years of experience building data pipelines, backend systems, and analytics infrastructure. I'm a backend/data hybrid — Spark, Airflow, SQL warehouses are home te...

#### 3. `CAND_0007655` — Senior Data Engineer
- **Industry**: Software | **Company**: Initech | **YoE**: 5.4
- **Skills**: Illustrator, TTS, GANs, Vue.js, Data Pipelines, scikit-learn, Diffusion Models, Computer Vision, Rust, REST APIs
- **Snippet**: Software / data professional with 5.4 years of experience building data pipelines, backend systems, and analytics infrastructure. I'm a backend/data hybrid — Spark, Airflow, SQL warehouses are home te...

---

### Exclusion Type: `CV/Speech/Robotics without NLP/IR exposure`

#### 1. `CAND_0001302` — Computer Vision Engineer
- **Industry**: Fintech | **Company**: Paytm | **YoE**: 5.8
- **Skills**: Time Series, Rust, Computer Vision, Diffusion Models, Learning to Rank, Python, OpenSearch, Forecasting, Kubeflow, TensorFlow
- **Snippet**: Data scientist / ML engineer with 5.8 years of experience in applied machine learning. Worked across predictive modeling, NLP, analytics, and lightweight deployment workflows. My current role is split...

#### 2. `CAND_0014909` — Computer Vision Engineer
- **Industry**: HealthTech AI | **Company**: Niramai | **YoE**: 4.8
- **Skills**: TTS, Python, pgvector, Hadoop, Reinforcement Learning, LangChain, Time Series, Speech Recognition, Prompt Engineering, Kubeflow
- **Snippet**: Data scientist / ML engineer with 4.8 years of experience in applied machine learning. Worked across predictive modeling, NLP, analytics, and lightweight deployment workflows. I've spent the last coup...

#### 3. `CAND_0034876` — Computer Vision Engineer
- **Industry**: AdTech | **Company**: InMobi | **YoE**: 3.5
- **Skills**: Object Detection, Statistical Modeling, Haystack, Computer Vision, pgvector, MLflow, Machine Learning, Weights & Biases, LoRA, Rust
- **Snippet**: Data scientist / ML engineer with 3.5 years of experience in applied machine learning. Worked across predictive modeling, NLP, analytics, and lightweight deployment workflows. I've been working on rec...

---

### Exclusion Type: `Flagged Honeypot`

#### 1. `CAND_0001610` — Machine Learning Engineer
- **Industry**: Gaming | **Company**: Dream11 | **YoE**: 3.0
- **Skills**: Speech Recognition, Haystack, Deep Learning, Kubeflow, Pinecone, Salesforce CRM, Feature Engineering, scikit-learn, Fine-tuning LLMs, Data Science
- **Snippet**: Machine learning engineer with 5.2 years of experience building ML-powered features in production. Strong background in NLP, recommendation systems, and applied AI; comfortable across the ML stack fro...

#### 2. `CAND_0003582` — Mobile Developer
- **Industry**: IT Services | **Company**: Mphasis | **YoE**: 8.2
- **Skills**: Docker, Image Classification, MLflow, Photoshop, TTS, Spring Boot, JavaScript, Content Writing
- **Snippet**: Software engineer with 8.2 years of experience across web, backend, and cloud systems. Strong fundamentals in software development and system design. My background is full-stack, but my comfort zone i...

#### 3. `CAND_0007353` — Frontend Engineer
- **Industry**: Conglomerate | **Company**: Wayne Enterprises | **YoE**: 9.9
- **Skills**: Tailwind, Apache Flink, Content Writing, Hadoop, RAG, Reinforcement Learning, Microservices
- **Snippet**: Software engineer with 9.9 years of experience across web, backend, and cloud systems. Strong fundamentals in software development and system design. I've worked across web frontends, REST APIs, and c...

---

## Section 3: Generic Non-Tech with ML/Search Exposure (10 Samples)

These candidates hold generic non-tech titles (Tier D, e.g. HR Manager) but mention AI/ML keywords in their career descriptions. We confirm that Layer 1 **retains** them (`eligible == True`) so that the Layer 2 hybrid search can evaluate them:

### 1. Candidate: `CAND_0000002`
- **Current Title**: Operations Manager | **Company**: Wipro
- **Mentions of ML**:
  - *Acme Corp*: ...Wrote longform articles on developer tools, cloud platforms, and AI/ML topics — including some that ranked on the first page of search for high-competition keywords...
  - *Acme Corp*: ...Wrote longform articles on developer tools, cloud platforms, and AI/ML topics — including some that ranked on the first page of search for high-competition keywords...


### 2. Candidate: `CAND_0000004`
- **Current Title**: Marketing Manager | **Company**: Dunder Mifflin
- **Mentions of ML**:
  - *Infosys*: ...Wrote longform articles on developer tools, cloud platforms, and AI/ML topics — including some that ranked on the first page of search for high-competition keywords...
  - *Infosys*: ...Wrote longform articles on developer tools, cloud platforms, and AI/ML topics — including some that ranked on the first page of search for high-competition keywords...


### 3. Candidate: `CAND_0000020`
- **Current Title**: Mechanical Engineer | **Company**: Wipro
- **Mentions of ML**:
  - *Dunder Mifflin*: ...Wrote longform articles on developer tools, cloud platforms, and AI/ML topics — including some that ranked on the first page of search for high-competition keywords...
  - *Dunder Mifflin*: ...Wrote longform articles on developer tools, cloud platforms, and AI/ML topics — including some that ranked on the first page of search for high-competition keywords...


### 4. Candidate: `CAND_0000022`
- **Current Title**: Mechanical Engineer | **Company**: Hooli
- **Mentions of ML**:
  - *Hooli*: ...Wrote longform articles on developer tools, cloud platforms, and AI/ML topics — including some that ranked on the first page of search for high-competition keywords...
  - *Hooli*: ...Wrote longform articles on developer tools, cloud platforms, and AI/ML topics — including some that ranked on the first page of search for high-competition keywords...


### 5. Candidate: `CAND_0000024`
- **Current Title**: HR Manager | **Company**: TCS
- **Mentions of ML**:
  - *Infosys*: ...Wrote longform articles on developer tools, cloud platforms, and AI/ML topics — including some that ranked on the first page of search for high-competition keywords...
  - *Infosys*: ...Wrote longform articles on developer tools, cloud platforms, and AI/ML topics — including some that ranked on the first page of search for high-competition keywords...


### 6. Candidate: `CAND_0000026`
- **Current Title**: Graphic Designer | **Company**: Initech
- **Mentions of ML**:
  - *Acme Corp*: ...Wrote longform articles on developer tools, cloud platforms, and AI/ML topics — including some that ranked on the first page of search for high-competition keywords...
  - *Acme Corp*: ...Wrote longform articles on developer tools, cloud platforms, and AI/ML topics — including some that ranked on the first page of search for high-competition keywords...


### 7. Candidate: `CAND_0000030`
- **Current Title**: Marketing Manager | **Company**: Dunder Mifflin
- **Mentions of ML**:
  - *Hooli*: ...Wrote longform articles on developer tools, cloud platforms, and AI/ML topics — including some that ranked on the first page of search for high-competition keywords...
  - *Hooli*: ...Wrote longform articles on developer tools, cloud platforms, and AI/ML topics — including some that ranked on the first page of search for high-competition keywords...


### 8. Candidate: `CAND_0000034`
- **Current Title**: Business Analyst | **Company**: Wipro
- **Mentions of ML**:
  - *Wipro*: ...Wrote longform articles on developer tools, cloud platforms, and AI/ML topics — including some that ranked on the first page of search for high-competition keywords...
  - *Wipro*: ...Wrote longform articles on developer tools, cloud platforms, and AI/ML topics — including some that ranked on the first page of search for high-competition keywords...


### 9. Candidate: `CAND_0000042`
- **Current Title**: HR Manager | **Company**: Wayne Enterprises
- **Mentions of ML**:
  - *Wayne Enterprises*: ...Wrote longform articles on developer tools, cloud platforms, and AI/ML topics — including some that ranked on the first page of search for high-competition keywords...
  - *Wayne Enterprises*: ...Wrote longform articles on developer tools, cloud platforms, and AI/ML topics — including some that ranked on the first page of search for high-competition keywords...


### 10. Candidate: `CAND_0000057`
- **Current Title**: Customer Support | **Company**: Acme Corp
- **Mentions of ML**:
  - *Infosys*: ...Wrote longform articles on developer tools, cloud platforms, and AI/ML topics — including some that ranked on the first page of search for high-competition keywords...
  - *Infosys*: ...Wrote longform articles on developer tools, cloud platforms, and AI/ML topics — including some that ranked on the first page of search for high-competition keywords...


