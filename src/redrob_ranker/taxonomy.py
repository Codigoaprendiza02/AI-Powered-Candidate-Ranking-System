# Taxonomy Definitions per PRD Appendix A and B

# 47 titles mapped to tiers (S: Core AI, A: Adjacent AI, B: Engineering/Data, C: Generic Tech, D: Non-tech)
TITLE_TAXO = {
    # Tier S - Core AI/ML/Search
    "Recommendation Systems Engineer": "S",
    "Search Engineer": "S",
    "Senior AI Engineer": "S",
    "Lead AI Engineer": "S",
    "Staff Machine Learning Engineer": "S",
    "Senior Machine Learning Engineer": "S",
    "Senior NLP Engineer": "S",
    "NLP Engineer": "S",
    "Machine Learning Engineer": "S",
    "Applied ML Engineer": "S",
    "ML Engineer": "S",
    "Senior Applied Scientist": "S",
    "Senior Data Scientist": "S",
    
    # Tier A - Adjacent AI/ML
    "AI Engineer": "A",
    "Data Scientist": "A",
    "Senior Software Engineer (ML)": "A",
    "Computer Vision Engineer": "A",
    "AI Research Engineer": "A",
    "AI Specialist": "A",
    "Junior ML Engineer": "A",
    
    # Tier B - Engineering & Data
    "Senior Data Engineer": "B",
    "Data Engineer": "B",
    "Analytics Engineer": "B",
    "Backend Engineer": "B",
    "Senior Software Engineer": "B",
    "Software Engineer": "B",
    "Data Analyst": "B",
    "Full Stack Developer": "B",
    "Cloud Engineer": "B",
    "DevOps Engineer": "B",
    
    # Tier C - Generic Tech
    "Java Developer": "C",
    ".NET Developer": "C",
    "Mobile Developer": "C",
    "Frontend Engineer": "C",
    "QA Engineer": "C",
    
    # Tier D - Non-tech
    "Business Analyst": "D",
    "HR Manager": "D",
    "Mechanical Engineer": "D",
    "Accountant": "D",
    "Project Manager": "D",
    "Customer Support": "D",
    "Operations Manager": "D",
    "Content Writer": "D",
    "Sales Executive": "D",
    "Civil Engineer": "D",
    "Graphic Designer": "D",
    "Marketing Manager": "D"
}

# Consulting-firm set (Appendix B)
CONSULTING_COMPANIES = {
    "TCS", "Infosys", "Wipro", "Accenture", "Cognizant", 
    "Capgemini", "Tech Mahindra", "Mindtree", "HCL"
}

# NLP/IR skill terms for Tier-A CV Engineer checks (Appendix A)
NLP_IR_SKILLS = {
    "nlp", "information retrieval", "embeddings", "sentence transformers", 
    "hugging face transformers", "rag", "llm", "sentence-transformers", 
    "bge", "e5", "vector search", "hybrid search", "retrieval", "semantic search",
    "vector db", "pinecone", "weaviate", "qdrant", "milvus", "faiss"
}
