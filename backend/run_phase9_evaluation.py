import os
import django
import urllib.request
import json
import time
from dataclasses import asdict

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from apps.accounts.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from apps.knowledge.evaluation.rag_evaluation_dataset import RAG_EVALUATION_CASES
from apps.knowledge.evaluation.rag_evaluator import evaluate_case
from apps.knowledge.evaluation.rag_experiment import Phase8Artifact

def run_evaluation():
    # 1. Authenticate
    try:
        user = User.objects.get(username='retrieval_evaluation')
    except User.DoesNotExist:
        print("User 'retrieval_evaluation' not found.")
        return

    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)

    print(f"Starting Phase 9 Evaluation on {len(RAG_EVALUATION_CASES)} cases...")

    # Initialize artifact
    artifact = Phase8Artifact(
        benchmark_id="rag-phase9-end-to-end-v1",
        phase="phase_9",
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        dataset_size=len(RAG_EVALUATION_CASES),
        category_distribution={
            c.category: sum(1 for x in RAG_EVALUATION_CASES if x.category == c.category)
            for c in RAG_EVALUATION_CASES
        },
        retrieval_config={
            "strategy": "semantic",
            "top_k": 5,
            "embedding_model": "all-MiniLM-L6-v2",
            "chunking": "production_default",
            "corpus": "evaluation_corpus",
            "filters": {},
            "similarity": "cosine",
        },
        generation_config={
            "service": "ollama_local",
            "model": "qwen3:4b-instruct-2507-q4_K_M",
            "temperature": "default_from_stack",
            "prompt_version": "build_rag_prompt_v1",
            "max_tokens": "default_from_stack",
        },
        notes="Actual end-to-end execution of Phase 9 evaluation."
    )

    per_case_results = []
    latencies = {"retrieval": [], "generation": [], "total": []}

    # Track overall metrics
    correct_count = 0
    total_coverage = 0
    grounded_count = 0
    source_aligned_count = 0
    expected_abstain = 0
    correct_abstain = 0
    cases_with_unsupported = 0

    fail_matrix = {
        "retrieval_failures": 0,
        "generation_failures": 0,
        "grounding_failures": 0
    }

    for idx, case in enumerate(RAG_EVALUATION_CASES):
        print(f"\nCase {idx+1}/{len(RAG_EVALUATION_CASES)}: [{case.category}] {case.query}")
        req = urllib.request.Request(
            'http://localhost:8000/api/v1/knowledge/ask/',
            data=json.dumps({'query': case.query}).encode('utf-8'),
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
        )

        answer_text = ""
        metrics = {}
        sources = []
        error = None

        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                for line in response:
                    line = line.decode('utf-8').strip()
                    if not line:
                        continue
                    if line.startswith('data: '):
                        data_str = line[6:]
                        if data_str.startswith('{'):
                            try:
                                data = json.loads(data_str)
                                if data.get('type') == 'done':
                                    metrics = data.get('metrics', {})
                                    sources = data.get('sources', [])
                                    break
                                elif data.get('type') == 'error':
                                    error = data.get('message')
                                    break
                            except json.JSONDecodeError:
                                answer_text += data_str
                        else:
                            answer_text += data_str
        except Exception as e:
            error = str(e)

        retrieved_titles = tuple(s.get('document_title', '') for s in sources)

        failure_class = "none"
        eval_result = None

        if error:
            failure_class = "request_error"
        else:
            eval_result = evaluate_case(case, answer_text, retrieved_titles)
            missing_relevant = set(case.relevant_document_titles) - set(retrieved_titles)

            # Attribution Logic
            if missing_relevant and not case.unanswerable:
                failure_class = "retrieval_failure"
                fail_matrix["retrieval_failures"] += 1
            elif not eval_result["expected_points_result"]["score"] == 1.0 and not case.unanswerable:
                failure_class = "generation_failure"
                fail_matrix["generation_failures"] += 1
            elif not eval_result["forbidden_result"]["passed"]:
                failure_class = "grounding_failure"
                fail_matrix["grounding_failures"] += 1
            elif case.unanswerable and not eval_result["abstention_result"]["detected_abstain"]:
                failure_class = "generation_failure"
                fail_matrix["generation_failures"] += 1

            # Stats aggregation
            if eval_result["passed"]:
                correct_count += 1
            total_coverage += eval_result["expected_points_result"]["score"]
            if eval_result["forbidden_result"]["passed"]:
                grounded_count += 1
            else:
                cases_with_unsupported += 1

            if eval_result["source_alignment_result"]["citation_coverage"] == 1.0:
                source_aligned_count += 1

            if case.unanswerable:
                expected_abstain += 1
                if eval_result["abstention_result"]["detected_abstain"]:
                    correct_abstain += 1

            if metrics:
                latencies["retrieval"].append(metrics.get("retrieval_ms", 0))
                latencies["generation"].append(metrics.get("generation_ms", 0))
                latencies["total"].append(metrics.get("total_ms", 0))

        # Store case result
        res = {
            "case_id": case.case_id,
            "category": case.category,
            "answer_category": case.answer_category,
            "unanswerable": case.unanswerable,
            "expected_points": list(case.expected_answer_points),
            "forbidden_claims": list(case.forbidden_claims),
            "retrieved_document_titles": list(retrieved_titles),
            "evaluation_method": "deterministic (points + forbidden + abstention + source_alignment)",
            "simulated_answer_evaluated": False,
            "actual_answer": answer_text,
            "error": error,
            "metrics": metrics,
            "eval_result": eval_result,
            "failure_class": failure_class,
        }
        per_case_results.append(res)

        print(f"  Retrieved titles: {retrieved_titles}")
        print(f"  Failure class: {failure_class}")
        if error:
            print(f"  Error: {error}")
        else:
            print(f"  Passed: {eval_result['passed']}")
            lat = metrics.get('total_ms', 0)
            print(f"  Total latency: {lat}ms")

    # Finalize Artifact
    import statistics
    def get_median(lst):
        return statistics.median(lst) if lst else None

    total_cases = len(RAG_EVALUATION_CASES)
    artifact.per_case_results = per_case_results

    artifact.overall_metrics = {
        "correctness_rate": correct_count / total_cases if total_cases else 0.0,
        "coverage_rate": total_coverage / total_cases if total_cases else 0.0,
        "groundedness_rate": grounded_count / total_cases if total_cases else 0.0,
        "abstention_correct_rate": correct_abstain / expected_abstain if expected_abstain else None,
        "unsupported_claim_rate": cases_with_unsupported / total_cases if total_cases else 0.0,
        "overall_pass_rate": correct_count / total_cases if total_cases else 0.0,
        "source_alignment_rate": source_aligned_count / total_cases if total_cases else 0.0,
    }

    artifact.latency_summary = {
        "median_retrieval_ms": get_median(latencies["retrieval"]),
        "median_generation_ms": get_median(latencies["generation"]),
        "median_total_ms": get_median(latencies["total"]),
        "note": "Measured end-to-end.",
    }

    artifact.notes += f"\nFailures -> Retrieval: {fail_matrix['retrieval_failures']}, Generation: {fail_matrix['generation_failures']}, Grounding: {fail_matrix['grounding_failures']}"

    with open("phase9_artifact.json", "w") as f:
        f.write(json.dumps(asdict(artifact), indent=2, default=str))
    print("\nEvaluation complete. Artifact written to phase9_artifact.json")

if __name__ == "__main__":
    run_evaluation()
