# How I Would Explain KnowledgeOS in an Interview

### 30-Second Explanation
KnowledgeOS is an enterprise AI platform that turns fragmented organizational data into a centralized, searchable knowledge system. It uses Retrieval-Augmented Generation (RAG) backed by PostgreSQL and pgvector to let employees ask questions in natural language. The system strictly enforces tenant isolation at the database level and uses a local LLM generation path to provide accurate, context-aware answers with citations, significantly reducing time spent searching for information.

### 2-Minute Technical Explanation
At its core, KnowledgeOS is a multi-tenant RAG application. The backend is built with Python and Django. When a user asks a question, the request is authenticated to determine their tenant scope (Organization ID). We embed the query using a local `all-MiniLM-L6-v2` model hosted in a dedicated microservice.

The retrieval layer queries a PostgreSQL database using `pgvector` for cosine similarity, filtering strictly by the user's organization. We retrieve the top 5 most relevant document chunks. These chunks form a strictly bounded context window injected into a RAG prompt. Finally, a local LLM (Qwen3) generates an answer based *only* on the provided context, complete with source citations.

To ensure this actually works in production, I built a deterministic 20-case evaluation pipeline measuring Recall, Precision, MRR, Correctness, Groundedness, and Abstention. Through rigorous evaluation, we established a solid baseline and deliberately chose not to over-engineer the retrieval layer with features like query-aware reranking or hybrid search, as the evidence showed they added latency without universally dominating our semantic baseline.

### Retrieval Deep Dive
Our retrieval baseline uses pure semantic search. Documents are processed into 1000-character chunks with a 150-character overlap, embedded into 384-dimensional vectors, and stored in pgvector.

We systematically tested alternatives: BM25 lexical search, Hybrid search, Reciprocal Rank Fusion (RRF), varying candidate pool sizes (K=10, 15, 20), and different chunking strategies. While some experiments like query-aware reranking improved specific metrics like Mean Reciprocal Rank (MRR), they caused slight declines in Precision@5, exhibited category-specific behavior, and added 50-100ms of API overhead. Similarly, increasing the candidate pool size provided diminishing returns on quality while linearly increasing latency. Therefore, we kept the baseline (K=5, pure semantic) as it provided the best observed trade-off on this evaluation set between speed, quality, and maintenance cost.

### RAG Evaluation Deep Dive
Evaluating RAG is notoriously difficult because LLM answers are non-deterministic and hard to score. I built a custom, deterministic evaluator that scores answers on Correctness, Answer-Point Coverage, Groundedness (proper citation of sources), Source Alignment, and Correct Abstention.

In Phase 9, our end-to-end benchmark across 20 categorized cases achieved a 90% overall pass rate. Crucially, it achieved 100% correct abstention on unanswerable queries and a 0% unsupported claim rate. A major engineering challenge was hardening the evaluator to eliminate false positives—for example, ensuring the evaluator could distinguish between the forbidden claim "authentication decides role" and the valid contrastive statement "authentication is separate from the role check."

### Why I Did Not Ship Every Experiment
Engineering is about trade-offs. It's tempting to ship complex architectures like Hybrid Retrieval, RRF, or cross-encoder reranking because they sound impressive. However, my evaluation pipeline showed that these additions often produced mixed metrics, required constant tuning, or added unacceptable latency (e.g., reranking added up to 100ms overhead).

Our semantic baseline achieved a 90% pass rate. Introducing complex, computationally expensive features for marginal or inconsistent gains violates conservative engineering principles. We kept those features experimental and only shipped what was supported by robust evidence.

### Hardest Engineering Problem
The hardest problem was eliminating false positives in the RAG evaluator. We needed to automatically detect if the LLM hallucinated a "forbidden claim". Initially, if the LLM generated a contrastive statement like "This mechanism separates identity verification from permission checks," the evaluator would flag it as a violation because it contained overlapping keywords with a forbidden claim ("authentication decides role").

I had to build a deterministic, negation-aware keyword matching system that parsed sentence structures for contrastive connectors (`while`, `whereas`, `separate from`) and parallel semicolon structures to accurately assess the LLM's true semantic intent without relying on a slow, secondary LLM as a judge.

### Most Important Failure Discovered
The most important failures discovered were `rag_p02` and `rag_h01`. In these cases, the LLM failed to include all expected answer points in its response (scoring < 0.5 for coverage).

This failure was critical because it proved our evaluator worked: it accurately distinguished between an LLM that was hallucinating (which we eliminated) and an LLM that was simply being too brief or missing nuance. It localized the remaining error strictly to generation quality, allowing us to defer targeted prompt tuning rather than tearing up the entire retrieval pipeline.

### What I Would Improve Next
Latency. Our median retrieval latency is around 15ms, but our local LLM generation takes roughly 10 seconds, dominating >99% of the total request time.

Future optimization efforts must focus strictly on the generation path. This means implementing response streaming to improve perceived latency, testing smaller or highly-quantized models, or implementing aggressive semantic caching for common queries. Optimizing the database retrieval any further would have zero practical impact on the user experience.
