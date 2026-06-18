# Exploratory Data Analysis & Schema Validation Report

Generated at: 2026-06-18 13:25:19
Dataset processed: `data/candidates.jsonl`
Elapsed time: 101.94 seconds

## 1. Summary of Dataset Integrity

| Metric | Value |
|---|---|
| Total candidates processed | 100,000 |
| Unique candidate IDs | 100,000 |
| Duplicate candidate IDs | 0 |
| Schema validation failures | 0 |
| Unique current titles | 47 |
| Average skills per candidate | 9.60 |
| Candidates with consulting-only careers | 8,991 (8.99%) |
| Candidates in target ML/AI/Search/Ranking titles | 1,179 (1.18%) |

## 2. Honeypot & Internal Consistency Heuristics

These heuristics match Section 1.1 of the PRD and identify potentially anomalous/adversarial candidate profiles:

| Heuristic | Description | Count | Percentage |
|---|---|---|---|
| **1. Skill-duration overflow** | `skills[].duration_months > years_of_experience × 12` | 13,449 | 13.45% |
| **2. Unverified expert** | `proficiency == "expert"` and `duration_months == 0` | 21 | 0.0210% |
| **3. Career-history overflow** | `sum(career_history.duration_months) > years_of_experience × 12 + 12` | 24 | 0.0240% |

## 3. Platform Signals Distribution (Redrob Signals)

Descriptive statistics for numeric engagement metrics across the dataset:

| Signal | Min | Max | Mean | 25% | Median (50%) | 75% |
|---|---|---|---|---|---|---|
| avg_response_time_hours | 2.10 | 280.00 | 132.70 | 68.30 | 129.90 | 193.30 |
| connection_count | 10.00 | 1898.00 | 345.66 | 174.00 | 335.00 | 497.00 |
| endorsements_received | 0.00 | 242.00 | 30.07 | 14.00 | 28.00 | 43.00 |
| github_activity_score | -1.00 | 96.90 | 9.62 | -1.00 | -1.00 | 16.70 |
| interview_completion_rate | 0.30 | 1.00 | 0.62 | 0.48 | 0.62 | 0.76 |
| notice_period_days | 0.00 | 150.00 | 87.39 | 60.00 | 90.00 | 120.00 |
| offer_acceptance_rate | -1.00 | 0.93 | -0.40 | -1.00 | -1.00 | 0.40 |
| profile_completeness_score | 25.00 | 99.90 | 56.76 | 42.20 | 56.80 | 71.60 |
| recruiter_response_rate | 0.02 | 0.95 | 0.44 | 0.25 | 0.44 | 0.62 |
| saved_by_recruiters_30d | 0.00 | 80.00 | 7.66 | 3.00 | 7.00 | 11.00 |
| search_appearance_30d | 0.00 | 1490.00 | 117.54 | 52.00 | 105.00 | 158.00 |

## 4. Current Title Taxonomy

Full taxonomy of all 47 unique `current_title` values:

| Title | Count | Percentage |
|---|---|---|
| Business Analyst | 5,833 | 5.833% |
| HR Manager | 5,830 | 5.830% |
| Mechanical Engineer | 5,791 | 5.791% |
| Accountant | 5,764 | 5.764% |
| Project Manager | 5,754 | 5.754% |
| Customer Support | 5,750 | 5.750% |
| Operations Manager | 5,744 | 5.744% |
| Content Writer | 5,727 | 5.727% |
| Sales Executive | 5,713 | 5.713% |
| Civil Engineer | 5,702 | 5.702% |
| Graphic Designer | 5,689 | 5.689% |
| Marketing Manager | 5,524 | 5.524% |
| Software Engineer | 3,450 | 3.450% |
| Full Stack Developer | 2,873 | 2.873% |
| Cloud Engineer | 2,836 | 2.836% |
| Java Developer | 2,809 | 2.809% |
| .NET Developer | 2,788 | 2.788% |
| DevOps Engineer | 2,787 | 2.787% |
| Mobile Developer | 2,757 | 2.757% |
| Frontend Engineer | 2,738 | 2.738% |
| QA Engineer | 2,682 | 2.682% |
| Analytics Engineer | 764 | 0.764% |
| Data Engineer | 744 | 0.744% |
| Data Analyst | 728 | 0.728% |
| Backend Engineer | 704 | 0.704% |
| Senior Data Engineer | 687 | 0.687% |
| Senior Software Engineer | 653 | 0.653% |
| ML Engineer | 167 | 0.167% |
| AI Research Engineer | 153 | 0.153% |
| Data Scientist | 145 | 0.145% |
| Senior Software Engineer (ML) | 142 | 0.142% |
| Computer Vision Engineer | 132 | 0.132% |
| Junior ML Engineer | 131 | 0.131% |
| AI Specialist | 130 | 0.130% |
| Recommendation Systems Engineer | 26 | 0.026% |
| Machine Learning Engineer | 24 | 0.024% |
| Applied ML Engineer | 23 | 0.023% |
| Search Engineer | 23 | 0.023% |
| AI Engineer | 21 | 0.021% |
| Senior Data Scientist | 19 | 0.019% |
| NLP Engineer | 14 | 0.014% |
| Senior NLP Engineer | 6 | 0.006% |
| Senior Machine Learning Engineer | 6 | 0.006% |
| Staff Machine Learning Engineer | 6 | 0.006% |
| Senior AI Engineer | 4 | 0.004% |
| Senior Applied Scientist | 4 | 0.004% |
| Lead AI Engineer | 3 | 0.003% |

## 5. Top 30 Companies

| Company | Count | Percentage |
|---|---|---|
| Infosys | 7,590 | 7.59% |
| Wayne Enterprises | 7,571 | 7.57% |
| Wipro | 7,566 | 7.57% |
| Initech | 7,528 | 7.53% |
| Pied Piper | 7,500 | 7.50% |
| Globex Inc | 7,492 | 7.49% |
| Acme Corp | 7,490 | 7.49% |
| Dunder Mifflin | 7,467 | 7.47% |
| TCS | 7,451 | 7.45% |
| Hooli | 7,378 | 7.38% |
| Stark Industries | 7,323 | 7.32% |
| Swiggy | 1,288 | 1.29% |
| Accenture | 1,274 | 1.27% |
| Capgemini | 1,265 | 1.26% |
| CRED | 1,257 | 1.26% |
| HCL | 1,250 | 1.25% |
| Razorpay | 1,246 | 1.25% |
| Zomato | 1,226 | 1.23% |
| Mindtree | 1,225 | 1.23% |
| Cognizant | 1,213 | 1.21% |
| Flipkart | 1,171 | 1.17% |
| Tech Mahindra | 1,168 | 1.17% |
| Mphasis | 1,153 | 1.15% |
| Meesho | 186 | 0.19% |
| InMobi | 172 | 0.17% |
| Nykaa | 172 | 0.17% |
| Zoho | 165 | 0.17% |
| Freshworks | 163 | 0.16% |
| Vedantu | 163 | 0.16% |
| Ola | 161 | 0.16% |

## 6. Top 30 Industries

| Industry | Count | Percentage |
|---|---|---|
| IT Services | 29,881 | 29.88% |
| Software | 22,417 | 22.42% |
| Manufacturing | 22,305 | 22.30% |
| Conglomerate | 7,571 | 7.57% |
| Paper Products | 7,467 | 7.47% |
| Fintech | 2,808 | 2.81% |
| Food Delivery | 2,514 | 2.51% |
| E-commerce | 1,529 | 1.53% |
| Consulting | 1,274 | 1.27% |
| EdTech | 610 | 0.61% |
| SaaS | 328 | 0.33% |
| AI/ML | 278 | 0.28% |
| AdTech | 172 | 0.17% |
| Transportation | 162 | 0.16% |
| Insurance Tech | 155 | 0.15% |
| Gaming | 149 | 0.15% |
| HealthTech | 147 | 0.15% |
| HealthTech AI | 68 | 0.07% |
| Conversational AI | 62 | 0.06% |
| AI Services | 42 | 0.04% |
| Voice AI | 31 | 0.03% |
| Internet | 22 | 0.02% |
| Media | 6 | 0.01% |
| Consumer Electronics | 2 | 0.00% |

