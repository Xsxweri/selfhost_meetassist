from app.services.memory_service import _rrf


def _hit(hid, content="x"):
    return {"id": hid, "content": content}


def test_rrf_empty():
    assert _rrf([]) == []
    assert _rrf([[], []]) == []


def test_rrf_single_list_preserves_order():
    out = _rrf([[_hit("a"), _hit("b")]])
    assert [r["id"] for r in out] == ["a", "b"]
    assert out[0]["score"] > out[1]["score"]


def test_rrf_boosts_doc_in_both_lists():
    """两路都命中的文档融合分应高于只命中一路的"""
    vec = [_hit("b"), _hit("a")]
    kw = [_hit("b")]
    out = _rrf([vec, kw])
    scores = {r["id"]: r["score"] for r in out}
    assert out[0]["id"] == "b"
    assert scores["b"] > scores["a"]


def test_rrf_dedup_keeps_single_row():
    out = _rrf([[_hit("a", "va")], [_hit("a", "va")]])
    assert len(out) == 1 and out[0]["id"] == "a"


def test_rrf_score_formula():
    """单路单文档 rank0 → 1/(k+rank+1)，k=60 → 1/61"""
    out = _rrf([[_hit("a")]])
    assert abs(out[0]["score"] - round(1 / 61, 6)) < 1e-9