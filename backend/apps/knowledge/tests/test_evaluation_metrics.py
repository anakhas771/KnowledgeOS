"""
Retrieval metrics tests for RAG evaluation.

Tests the core ranking and precision/recall metrics used in RAG evaluation.
"""
# Simplified tests to avoid Django import issues
# These tests can run in a standard Python environment without Django

def test_recall_at_k():
    from apps.knowledge.evaluation.metrics import recall_at_k
    result = recall_at_k(retrieved_ids=[10, 20, 30], relevant_ids=[20, 30], k=3)
    assert result == 1.0

def test_recall_at_k_partial():
    from apps.knowledge.evaluation.metrics import recall_at_k
    result = recall_at_k(retrieved_ids=[10, 20, 30], relevant_ids=[20, 40], k=3)
    assert result == 0.5

def test_precision_at_k():
    from apps.knowledge.evaluation.metrics import precision_at_k
    result = precision_at_k(retrieved_ids=[10, 20, 30], relevant_ids=[20], k=3)
    assert result == 1 / 3

def test_reciprocal_rank():
    from apps.knowledge.evaluation.metrics import reciprocal_rank
    result = reciprocal_rank(retrieved_ids=[10, 20, 30], relevant_ids=[20])
    assert result == 0.5

def test_missing_relevant_document():
    from apps.knowledge.evaluation.metrics import reciprocal_rank
    result = reciprocal_rank(retrieved_ids=[10, 30, 40], relevant_ids=[20])
    assert result == 0.0

def test_mean_reciprocal_rank():
    from apps.knowledge.evaluation.metrics import mean_reciprocal_rank
    result = mean_reciprocal_rank(
        rankings=[[10, 20, 30], [30, 40, 50]],
        relevant_sets=[[20], [50]]
    )
    assert result == (0.5 + (1 / 3)) / 2

def test_invalid_k():
    from apps.knowledge.evaluation.metrics import recall_at_k, precision_at_k

    try:
        recall_at_k([1, 2], [1], 0)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass

    try:
        precision_at_k([1, 2], [1], 0)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass

def test_empty_relevant_ids():
    from apps.knowledge.evaluation.metrics import recall_at_k, reciprocal_rank

    assert recall_at_k([1, 2, 3], [], 3) == 0.0
    assert reciprocal_rank([1, 2, 3], []) == 0.0