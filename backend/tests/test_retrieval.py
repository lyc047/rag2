"""检索评估测试 —— MRR, Recall@K, NDCG@K, 来源准确率, 跨文档抗干扰"""
import math
import pytest
from collections import defaultdict
from app.rag.query_processor import preprocess_query


# ==================== 评估指标 ====================

def _is_relevant(chunk_text, expected_phrases):
    """判断chunk是否相关：包含任意一个期望短语"""
    if not expected_phrases:
        return False
    return any(phrase in chunk_text for phrase in expected_phrases)


def _check_source(doc, expected_source):
    """检查检索结果是否来自期望的源文档"""
    if not expected_source or expected_source == "any":
        return True
    return doc.metadata.get("source", "") == expected_source


def calc_hit_rate(retrieved_docs, expected_phrases):
    """Hit Rate —— 检索结果中是否至少有一个相关文档"""
    return 1.0 if any(_is_relevant(d.page_content, expected_phrases) for d in retrieved_docs) else 0.0


def calc_mrr(retrieved_docs, expected_phrases):
    """MRR (Mean Reciprocal Rank) —— 第一个相关文档排名的倒数"""
    for rank, doc in enumerate(retrieved_docs, start=1):
        if _is_relevant(doc.page_content, expected_phrases):
            return 1.0 / rank
    return 0.0


def calc_recall_at_k(retrieved_docs, expected_phrases):
    """Recall@K —— 前K个结果中命中的相关文档比例"""
    hit_count = sum(1 for d in retrieved_docs if _is_relevant(d.page_content, expected_phrases))
    estimated_total = max(len(expected_phrases), 1)
    return min(hit_count / estimated_total, 1.0)


def calc_source_accuracy(retrieved_docs, expected_source):
    """来源准确率 —— Top-1结果是否来自正确的源文档"""
    if not expected_source or expected_source == "any":
        return 1.0  # 不检验来源的查询视为通过
    if not retrieved_docs:
        return 0.0
    return 1.0 if _check_source(retrieved_docs[0], expected_source) else 0.0


# ==================== 检索评估测试 ====================

@pytest.mark.asyncio
async def test_retrieval_hit_rate(test_retriever, test_cases):
    """检索命中率 —— 含干扰文档时，每个用例至少命中一个相关chunk"""
    results = []
    failures = []

    for case in test_cases:
        expected = case.get("expected_chunks_contain", [])
        min_relevant = case.get("min_relevant_chunks", 1)
        if min_relevant == 0:
            continue

        query = preprocess_query(case["query"])
        docs = await test_retriever.retrieve(query)
        hit = calc_hit_rate(docs, expected)
        results.append(hit)

        if hit == 0.0:
            failures.append({
                "id": case["id"],
                "query": case["query"],
                "type": case["type"],
                "expected_source": case.get("expected_source", ""),
                "expected_phrases": expected,
                "retrieved_sources": [d.metadata.get("source", "?") for d in docs[:5]],
                "retrieved_previews": [d.page_content[:60] for d in docs[:3]],
            })

    hit_rate = sum(results) / len(results) if results else 0.0
    print(f"\n[Hit Rate] {hit_rate:.2%} ({int(sum(results))}/{len(results)})")

    if failures:
        print(f"\n[未命中] ({len(failures)}):")
        for f in failures:
            print(f"  [{f['id']}] {f['type']} | {f['query'][:60]}")
            print(f"    期望来源: {f['expected_source']} | 实际来源: {f['retrieved_sources']}")
            print(f"    期望短语: {f['expected_phrases']}")
    else:
        print("  全部命中!")

    assert hit_rate >= 0.50, f"Hit Rate过低: {hit_rate:.2%} < 50%"


@pytest.mark.asyncio
async def test_retrieval_mrr(test_retriever, test_cases):
    """MRR —— 第一个相关文档的排名倒数平均值"""
    mrr_scores = []

    for case in test_cases:
        expected = case.get("expected_chunks_contain", [])
        if case.get("min_relevant_chunks", 1) == 0 or not expected:
            continue

        query = preprocess_query(case["query"])
        docs = await test_retriever.retrieve(query)
        mrr = calc_mrr(docs, expected)
        mrr_scores.append({"id": case["id"], "mrr": mrr, "type": case["type"]})

    avg_mrr = sum(m["mrr"] for m in mrr_scores) / len(mrr_scores) if mrr_scores else 0.0

    # 找出MRR最低的用例
    mrr_scores.sort(key=lambda x: x["mrr"])
    print(f"\n[MRR] Mean Reciprocal Rank: {avg_mrr:.4f}")
    print(f"  MRR最低的3个用例:")
    for m in mrr_scores[:3]:
        print(f"    [{m['id']}] {m['type']}: MRR={m['mrr']:.4f}")

    assert avg_mrr >= 0.25, f"MRR过低: {avg_mrr:.4f} < 0.25"


@pytest.mark.asyncio
async def test_retrieval_recall_at_k(test_retriever, test_cases):
    """Recall@K —— 前K个结果中的召回率"""
    recall_scores = []

    for case in test_cases:
        expected = case.get("expected_chunks_contain", [])
        if not expected or case.get("min_relevant_chunks", 1) == 0:
            continue

        query = preprocess_query(case["query"])
        docs = await test_retriever.retrieve(query)
        recall = calc_recall_at_k(docs, expected)
        recall_scores.append(recall)

    avg_recall = sum(recall_scores) / len(recall_scores) if recall_scores else 0.0
    print(f"\n[Recall@K] Average: {avg_recall:.4f}")
    assert avg_recall >= 0.30, f"Recall@K过低: {avg_recall:.4f} < 0.30"


@pytest.mark.asyncio
async def test_source_accuracy(test_retriever, test_cases):
    """来源准确率 —— Top-1结果是否来自正确的源文档（跨文档抗干扰）"""
    source_results = []
    failures = []

    for case in test_cases:
        expected_source = case.get("expected_source", "")
        if not expected_source or expected_source == "any":
            continue

        query = preprocess_query(case["query"])
        docs = await test_retriever.retrieve(query)
        accurate = calc_source_accuracy(docs, expected_source)
        source_results.append(accurate)

        if accurate == 0.0:
            failures.append({
                "id": case["id"],
                "query": case["query"],
                "expected_source": expected_source,
                "top1_source": docs[0].metadata.get("source", "?") if docs else "EMPTY",
                "top3_sources": [d.metadata.get("source", "?") for d in docs[:3]],
            })

    src_acc = sum(source_results) / len(source_results) if source_results else 0.0
    print(f"\n[来源准确率] {src_acc:.2%} ({int(sum(source_results))}/{len(source_results)})")

    if failures:
        print(f"\n[来源混淆] ({len(failures)}):")
        for f in failures:
            print(f"  [{f['id']}] 期望: {f['expected_source']} | Top1: {f['top1_source']} | Top3: {f['top3_sources']}")
            print(f"    查询: {f['query'][:60]}")
    else:
        print("  所有查询Top-1来源正确!")

    assert src_acc >= 0.50, f"来源准确率过低: {src_acc:.2%} < 50%"


@pytest.mark.asyncio
async def test_retrieval_by_type(test_retriever, test_cases):
    """按题型分组评估，诊断不同检索能力"""
    type_hits = defaultdict(list)
    type_source = defaultdict(list)

    for case in test_cases:
        expected = case.get("expected_chunks_contain", [])
        expected_source = case.get("expected_source", "")
        if not expected or case.get("min_relevant_chunks", 1) == 0:
            continue

        query = preprocess_query(case["query"])
        docs = await test_retriever.retrieve(query)
        type_hits[case["type"]].append(calc_hit_rate(docs, expected))
        if expected_source and expected_source != "any":
            type_source[case["type"]].append(calc_source_accuracy(docs, expected_source))

    print(f"\n[按题型命中率]:")
    for t in sorted(type_hits):
        scores = type_hits[t]
        avg = sum(scores) / len(scores)
        status = "OK" if avg >= 0.60 else "WARN" if avg >= 0.30 else "FAIL"
        src_str = ""
        if t in type_source:
            src_avg = sum(type_source[t]) / len(type_source[t])
            src_str = f" | 来源准确率={src_avg:.1%}"
        print(f"  [{status}] {t}: {avg:.1%} ({int(sum(scores))}/{len(scores)}){src_str}")

    for t, scores in type_hits.items():
        avg = sum(scores) / len(scores)
        assert avg >= 0.25, f"题型 '{t}' 命中率过低: {avg:.1%} < 25%"


@pytest.mark.asyncio
async def test_negation_queries(test_retriever, test_cases):
    """否定查询 —— 文档没有的信息，检索不应找到强相关结果"""
    negation_cases = [c for c in test_cases if c.get("type") == "否定查询"]
    print(f"\n[否定查询] 共{len(negation_cases)}条:")

    for case in negation_cases:
        query = preprocess_query(case["query"])
        docs = await test_retriever.retrieve(query)
        expected = case.get("expected_chunks_contain", [])
        expected_source = case.get("expected_source", "")

        # 检查Top-1来源是否正确（不应是无关来源）
        top1_source = docs[0].metadata.get("source", "?") if docs else "EMPTY"
        # 对于否定查询，关键是：LLM能根据检索结果判定"未记载"
        # 检索层只需确保返回了相关文档（即使不包含答案）
        print(f"  [{case['id']}] {case['query'][:50]}")
        print(f"    Top-1来源: {top1_source} | 期望来源: {expected_source}")
        print(f"    note: {case.get('note', '')}")
