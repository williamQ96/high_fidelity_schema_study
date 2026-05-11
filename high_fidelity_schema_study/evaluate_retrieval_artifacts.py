from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple


ROOT = Path(__file__).resolve().parent
RETRIEVAL_ROOT = ROOT / "data" / "retrieval" / "external_candidate_pool"
ARTIFACT_MANIFEST_PATH = RETRIEVAL_ROOT / "artifact_manifest.json"
REPORT_JSON_PATH = RETRIEVAL_ROOT / "retrieval_report.json"
REPORT_MD_PATH = RETRIEVAL_ROOT / "retrieval_report.md"


TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "find", "for", "from",
    "in", "is", "it", "of", "on", "or", "the", "to", "with",
}


def load_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def tokenize(text: str) -> List[str]:
    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    return [token.lower() for token in TOKEN_RE.findall(normalized) if token.lower() not in STOPWORDS]


def build_tfidf(documents: List[Dict[str, str]]) -> Tuple[List[Counter], Dict[str, float]]:
    tokenized_docs = [tokenize(document["text"]) for document in documents]
    doc_freq = Counter()
    for tokens in tokenized_docs:
        doc_freq.update(set(tokens))

    total_docs = len(documents)
    idf = {term: math.log((1 + total_docs) / (1 + freq)) + 1.0 for term, freq in doc_freq.items()}

    vectors = []
    for tokens in tokenized_docs:
        tf = Counter(tokens)
        vector = Counter({term: count * idf.get(term, 0.0) for term, count in tf.items()})
        vectors.append(vector)

    return vectors, idf


def build_query_vector(text: str, idf: Dict[str, float]) -> Counter:
    tokens = tokenize(text)
    tf = Counter(tokens)
    return Counter({term: count * idf.get(term, 0.0) for term, count in tf.items()})


def cosine_similarity(vec_a: Counter, vec_b: Counter) -> float:
    dot = sum(vec_a[term] * vec_b.get(term, 0.0) for term in vec_a)
    norm_a = math.sqrt(sum(value * value for value in vec_a.values()))
    norm_b = math.sqrt(sum(value * value for value in vec_b.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def rank_documents(documents: List[Dict[str, str]], query_text: str) -> Tuple[List[Dict[str, str]], List[Counter], Counter]:
    doc_vectors, idf = build_tfidf(documents)
    query_vector = build_query_vector(query_text, idf)
    ranked = []
    for document, doc_vector in zip(documents, doc_vectors):
        ranked.append(
            {
                "candidate_id": document["candidate_id"],
                "title": document["title"],
                "score": round(cosine_similarity(query_vector, doc_vector), 6),
                "text": document["text"],
            }
        )
    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked, doc_vectors, query_vector


def reciprocal_rank(ranked: List[Dict[str, str]], expected_id: str) -> float:
    for index, item in enumerate(ranked, start=1):
        if item["candidate_id"] == expected_id:
            return 1.0 / index
    return 0.0


def recall_at_k(ranked: List[Dict[str, str]], expected_id: str, k: int) -> float:
    return 1.0 if any(item["candidate_id"] == expected_id for item in ranked[:k]) else 0.0


def precision_at_k(ranked: List[Dict[str, str]], expected_id: str, k: int) -> float:
    hits = sum(1 for item in ranked[:k] if item["candidate_id"] == expected_id)
    return hits / k


def ndcg_at_k(ranked: List[Dict[str, str]], expected_id: str, k: int) -> float:
    for index, item in enumerate(ranked[:k], start=1):
        if item["candidate_id"] == expected_id:
            return 1.0 / math.log2(index + 1)
    return 0.0


def overlap_terms(query_text: str, document_text: str) -> List[str]:
    query_terms = set(tokenize(query_text))
    doc_terms = set(tokenize(document_text))
    return sorted(query_terms & doc_terms)[:10]


def evaluate_artifact(artifact_name: str, documents: List[Dict[str, str]], queries: List[Dict[str, str]]) -> Dict:
    query_results = []
    recall_1 = []
    recall_3 = []
    precision_1 = []
    precision_3 = []
    mrr_values = []
    ndcg_3 = []

    for query in queries:
        ranked, _, _ = rank_documents(documents, query["text"])
        top_match = ranked[0]
        query_results.append(
            {
                "query_id": query["query_id"],
                "expected_candidate_id": query["expected_candidate_id"],
                "top_3": ranked[:3],
                "top_1_correct": top_match["candidate_id"] == query["expected_candidate_id"],
                "top_1_overlap_terms": overlap_terms(query["text"], top_match["text"]),
            }
        )
        recall_1.append(recall_at_k(ranked, query["expected_candidate_id"], 1))
        recall_3.append(recall_at_k(ranked, query["expected_candidate_id"], 3))
        precision_1.append(precision_at_k(ranked, query["expected_candidate_id"], 1))
        precision_3.append(precision_at_k(ranked, query["expected_candidate_id"], 3))
        mrr_values.append(reciprocal_rank(ranked, query["expected_candidate_id"]))
        ndcg_3.append(ndcg_at_k(ranked, query["expected_candidate_id"], 3))

    return {
        "artifact_name": artifact_name,
        "query_count": len(queries),
        "metrics": {
            "recall_at_1": round(sum(recall_1) / len(recall_1), 4),
            "recall_at_3": round(sum(recall_3) / len(recall_3), 4),
            "precision_at_1": round(sum(precision_1) / len(precision_1), 4),
            "precision_at_3": round(sum(precision_3) / len(precision_3), 4),
            "mrr": round(sum(mrr_values) / len(mrr_values), 4),
            "ndcg_at_3": round(sum(ndcg_3) / len(ndcg_3), 4),
        },
        "queries": query_results,
    }


def render_markdown(report: Dict) -> str:
    lines = [
        "# Retrieval Report",
        "",
        "This report compares lexical retrieval behavior over the current promoted external candidate pool.",
        "",
    ]
    for artifact in report["artifacts"]:
        lines.extend(
            [
                f"## {artifact['artifact_name']}",
                "",
                "| Metric | Value |",
                "| --- | ---: |",
            ]
        )
        for metric, value in artifact["metrics"].items():
            lines.append(f"| {metric} | {value:.4f} |")

        lines.extend(["", "### Query Cases", ""])
        for query in artifact["queries"]:
            top1 = query["top_3"][0]
            lines.extend(
                [
                    f"#### {query['query_id']}",
                    "",
                    f"- Expected: `{query['expected_candidate_id']}`",
                    f"- Top 1: `{top1['candidate_id']}`",
                    f"- Top 1 correct: `{query['top_1_correct']}`",
                    f"- Overlap terms: `{', '.join(query['top_1_overlap_terms'])}`" if query["top_1_overlap_terms"] else "- Overlap terms: none",
                    "",
                ]
            )
    return "\n".join(lines) + "\n"


def main() -> None:
    manifest = load_json(ARTIFACT_MANIFEST_PATH)
    queries = load_json(ROOT / "data" / manifest["artifact_files"]["queries"])["queries"]

    preferred_order = [
        "metadata_only",
        "readme_only",
        "schema_enhanced",
        "schema_enhanced_deterministic",
        "schema_enhanced_semantic_merged",
    ]
    artifact_names = [
        name
        for name in preferred_order
        if name in manifest["artifact_files"] and name != "queries"
    ]
    artifact_names.extend(
        name
        for name in manifest["artifact_files"]
        if name not in set(artifact_names) and name != "queries"
    )
    artifacts = []
    for artifact_name in artifact_names:
        documents = load_json(ROOT / "data" / manifest["artifact_files"][artifact_name])["documents"]
        artifacts.append(evaluate_artifact(artifact_name, documents, queries))
    report = {"artifacts": artifacts}
    REPORT_JSON_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    REPORT_MD_PATH.write_text(render_markdown(report), encoding="utf-8")


if __name__ == "__main__":
    main()
