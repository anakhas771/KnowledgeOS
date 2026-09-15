import json
import os
import time
import urllib.request
import urllib.error
import statistics
from collections import defaultdict

from django.core.management.base import BaseCommand
from rest_framework_simplejwt.tokens import RefreshToken
from apps.accounts.models import User

from apps.knowledge.evaluation.rag_evaluation_dataset import RAG_EVALUATION_CASES
from apps.knowledge.evaluation.rag_evaluator import evaluate_case

def _parse_sse(response) -> tuple[str, dict, dict]:
    answer_text = ""
    sources = []
    metrics = {}

    for line in response:
        line_str = line.decode('utf-8').strip()
        if not line_str.startswith("data: "):
            continue

        payload = line_str[len("data: "):]
        try:
            data = json.loads(payload)
            if isinstance(data, dict):
                if data.get("type") == "done":
                    sources = data.get("sources", [])
                    metrics = data.get("metrics", {})
                elif data.get("type") == "error":
                    answer_text += "[ERROR: " + data.get("detail", "") + "]"
            else:
                answer_text += str(data)
        except json.JSONDecodeError:
            answer_text += payload

    return answer_text, sources, metrics

def _classify_failure(case, eval_result, retrieved_titles):
    if eval_result["passed"]:
        return "N/A"

    missing_relevant = set(case.relevant_document_titles) - set(retrieved_titles)
    has_missing_evidence = len(missing_relevant) > 0 and len(case.relevant_document_titles) > 0

    if eval_result["expected_points_result"]["score"] < 0.5:
        if has_missing_evidence:
            return "A. retrieval failure"
        else:
            return "C. generation failure"

    if not eval_result["forbidden_result"]["passed"]:
        return "C. generation failure"

    if not eval_result["abstention_result"]["passed"]:
        if has_missing_evidence:
            return "C. generation failure (failed to abstain without evidence)"
        else:
            return "C. generation failure"

    if eval_result["source_alignment_result"]["citation_coverage"] < 0.5:
        return "D. grounding/source-alignment failure"

    return "E. unknown"

class Command(BaseCommand):
    help = "Run Phase 9 RAG E2E benchmark"

    def handle(self, *args, **options):
        self.stdout.write("Starting Phase 9 RAG E2E benchmark...")

        try:
            user = User.objects.get(username='retrieval_evaluation')
        except User.DoesNotExist:
            self.stderr.write("User 'retrieval_evaluation' not found.")
            return

        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        results = []
        metrics_list = []

        for case in RAG_EVALUATION_CASES:
            self.stdout.write(f"Evaluating {case.case_id} ({case.category})")

            req = urllib.request.Request(
                'http://localhost:8000/api/v1/knowledge/ask/',
                data=json.dumps({'query': case.query}).encode('utf-8'),
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                }
            )

            answer_text = ""
            sources = []
            metrics = {}
            try:
                with urllib.request.urlopen(req) as response:
                    answer_text, sources, metrics = _parse_sse(response)
            except urllib.error.HTTPError as e:
                self.stderr.write(f"HTTPError querying API: {e.code} {e.reason} - {e.read().decode('utf-8')}")
            except Exception as e:
                self.stderr.write(f"Failed to query API: {e}")

            retrieved_titles = tuple(s.get("document_title") for s in sources)
            eval_result = evaluate_case(case, answer_text, retrieved_titles)

            failure_class = _classify_failure(case, eval_result, retrieved_titles)

            results.append({
                "case_id": case.case_id,
                "question": case.query,
                "category": case.category,
                "answer": answer_text,
                "retrieved_sources": sources,
                "expected_relevant_sources": case.relevant_document_titles,
                "evaluation_scores": eval_result,
                "failure_classification": failure_class,
                "latency": metrics
            })

            metrics_list.append({
                "passed": eval_result["passed"],
                "points_score": eval_result["expected_points_result"]["score"],
                "grounded": eval_result["forbidden_result"]["passed"] and eval_result["source_alignment_result"]["citation_coverage"] >= 0.5,
                "source_alignment": eval_result["source_alignment_result"]["citation_coverage"],
                "abstention": eval_result["abstention_result"]["passed"] if case.unanswerable else None,
                "unsupported_claim": not eval_result["forbidden_result"]["passed"],
                "latency": metrics,
                "category": case.category
            })

            time.sleep(1) # brief pause between cases

        # Compute aggregate metrics
        total = len(metrics_list)
        correctness_rate = sum(1 for m in metrics_list if m["passed"]) / total if total else 0
        coverage_rate = statistics.mean(m["points_score"] for m in metrics_list) if total else 0
        groundedness_rate = sum(1 for m in metrics_list if m["grounded"]) / total if total else 0
        source_alignment_rate = statistics.mean(m["source_alignment"] for m in metrics_list) if total else 0

        unanswerable_cases = [m for m in metrics_list if m["abstention"] is not None]
        if unanswerable_cases:
            abstention_correct_rate = sum(1 for m in unanswerable_cases if m["abstention"]) / len(unanswerable_cases)
        else:
            abstention_correct_rate = None

        unsupported_claim_rate = sum(1 for m in metrics_list if m["unsupported_claim"]) / total if total else 0

        # Latency
        retrieval_ms = [m["latency"].get("retrieval_ms", 0) for m in metrics_list if isinstance(m["latency"], dict) and "retrieval_ms" in m["latency"]]
        generation_ms = [m["latency"].get("generation_ms", 0) for m in metrics_list if isinstance(m["latency"], dict) and "generation_ms" in m["latency"]]
        total_ms = [m["latency"].get("total_ms", 0) for m in metrics_list if isinstance(m["latency"], dict) and "total_ms" in m["latency"]]

        median_retrieval_ms = statistics.median(retrieval_ms) if retrieval_ms else 0
        median_generation_ms = statistics.median(generation_ms) if generation_ms else 0
        median_total_ms = statistics.median(total_ms) if total_ms else 0

        # Category metrics
        category_metrics = defaultdict(lambda: {"total": 0, "passed": 0, "points": [], "grounded": 0, "alignment": [], "abstention": [], "unsupported": 0})
        for m in metrics_list:
            cat = m["category"]
            c = category_metrics[cat]
            c["total"] += 1
            if m["passed"]: c["passed"] += 1
            c["points"].append(m["points_score"])
            if m["grounded"]: c["grounded"] += 1
            c["alignment"].append(m["source_alignment"])
            if m["abstention"] is not None: c["abstention"].append(m["abstention"])
            if m["unsupported_claim"]: c["unsupported"] += 1

        for cat, c in category_metrics.items():
            c["correctness"] = c["passed"] / c["total"]
            c["coverage"] = statistics.mean(c["points"])
            c["groundedness"] = c["grounded"] / c["total"]
            c["source_alignment"] = statistics.mean(c["alignment"])
            c["abstention_rate"] = statistics.mean(c["abstention"]) if c["abstention"] else None
            c["unsupported_rate"] = c["unsupported"] / c["total"]

        # Failure attribution
        failures = [r["failure_classification"] for r in results if r["failure_classification"] != "N/A"]
        failure_summary = {k: failures.count(k) for k in set(failures)}

        artifact = {
            "benchmark_id": "rag-phase9-empirical-v1",
            "phase": "phase_9",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "dataset_size": total,
            "category_distribution": {k: v["total"] for k, v in category_metrics.items()},
            "retrieval_config": {
                "strategy": "semantic",
                "top_k": 5,
                "embedding_model": "all-MiniLM-L6-v2",
                "chunking": "production_default",
                "corpus": "evaluation_corpus",
                "similarity": "cosine",
            },
            "generation_config": {
                "service": "ollama_local",
                "model": "qwen3:4b-instruct-2507-q4_K_M",
                "prompt_version": "build_rag_prompt_v1",
            },
            "overall_metrics": {
                "correctness_rate": correctness_rate,
                "coverage_rate": coverage_rate,
                "groundedness_rate": groundedness_rate,
                "source_alignment_rate": source_alignment_rate,
                "abstention_correct_rate": abstention_correct_rate,
                "unsupported_claim_rate": unsupported_claim_rate,
                "overall_pass_rate": correctness_rate,
            },
            "category_metrics": dict(category_metrics),
            "failure_summary": failure_summary,
            "latency_summary": {
                "median_retrieval_ms": median_retrieval_ms,
                "median_generation_ms": median_generation_ms,
                "median_total_ms": median_total_ms,
                "note": "Empirical latency from single-threaded sequential run",
            },
            "per_case_results": results
        }

        with open("phase9_artifact.json", "w") as f:
            f.write(json.dumps(artifact, indent=2, default=str))

        self.stdout.write("Evaluation complete. Wrote phase9_artifact.json")
