"""Tests for StaticCache."""

import json
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from wqb_mcp.client.static_cache import StaticCache, _INDEX_VERSION
from wqb_mcp.client.data import DataDatasetItem, DataDatasetsResponse, DataFieldItem, DataFieldsResponse
from wqb_mcp.client.operators import OperatorItem, OperatorsResponse
from wqb_mcp.client.user import PyramidMultiplierItem, PyramidMultipliersResponse
from wqb_mcp.client.community import TutorialsResponse, TutorialPageResponse
from wqb_mcp.client.simulation import SimulationSettingOptionsResponse


@pytest.fixture
def cache(tmp_path):
    return StaticCache(root=tmp_path)


# ---------------------------------------------------------------------------
# write_table / read_table basics
# ---------------------------------------------------------------------------

class TestWriteReadTable:
    def test_round_trip_flat_rows(self, cache):
        rows = [{"id": "a", "value": 1}, {"id": "b", "value": 2}]
        cache.write_table("test:flat", rows, ttl_days=7, file_subpath="test/flat.csv")
        back = cache.read_table("test:flat")
        assert back is not None
        assert len(back) == 2
        assert back[0]["id"] == "a"
        assert back[1]["value"] == 2

    def test_round_trip_nested_rows(self, cache):
        rows = [
            {"id": "ds1", "category": {"id": "c1", "name": "Sent"}, "themes": ["t1", "t2"]},
            {"id": "ds2", "category": {"id": "c2", "name": "Fund"}, "themes": []},
        ]
        cache.write_table("test:nested", rows, ttl_days=7, file_subpath="test/nested.csv")
        back = cache.read_table("test:nested")
        assert back[0]["category"] == {"id": "c1", "name": "Sent"}
        assert back[0]["themes"] == ["t1", "t2"]
        assert back[1]["themes"] == []

    def test_csv_file_written(self, cache, tmp_path):
        rows = [{"id": "a", "name": "Alpha"}]
        cache.write_table("test:csv", rows, ttl_days=7, file_subpath="test/data.csv")
        assert (tmp_path / "test/data.csv").exists()

    def test_empty_rows_not_written(self, cache):
        cache.write_table("test:empty", [], ttl_days=7, file_subpath="test/empty.csv")
        assert not cache.is_valid("test:empty")


# ---------------------------------------------------------------------------
# write_dict / read_dict basics
# ---------------------------------------------------------------------------

class TestWriteReadDict:
    def test_round_trip(self, cache):
        data = {"count": 2, "results": [{"id": "a"}, {"id": "b"}]}
        cache.write_dict("test:dict", data, ttl_days=30, file_subpath="test/dict.json")
        back = cache.read_dict("test:dict")
        assert back == data

    def test_nested_structure(self, cache):
        data = {
            "instrument_options": [{"type": "EQUITY", "regions": ["USA", "EUR"]}],
            "total_combinations": 1,
        }
        cache.write_dict("test:settings", data, ttl_days=30, file_subpath="test/settings.json")
        back = cache.read_dict("test:settings")
        assert back["instrument_options"][0]["regions"] == ["USA", "EUR"]


# ---------------------------------------------------------------------------
# TTL expiry
# ---------------------------------------------------------------------------

class TestTTL:
    def test_valid_entry(self, cache):
        cache.write_table("test:ttl", [{"id": "a"}], ttl_days=7, file_subpath="test/ttl.csv")
        assert cache.is_valid("test:ttl")

    def test_expired_entry(self, cache, tmp_path):
        cache.write_table("test:exp", [{"id": "a"}], ttl_days=7, file_subpath="test/exp.csv")
        # Manually backdate the cached_at
        idx = cache._load_index()
        old_time = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
        idx["entries"]["test:exp"]["cached_at"] = old_time
        cache._save_index()
        assert not cache.is_valid("test:exp")
        assert cache.read_table("test:exp") is None

    def test_nonexistent_key(self, cache):
        assert not cache.is_valid("nonexistent")
        assert cache.read_table("nonexistent") is None
        assert cache.read_dict("nonexistent") is None


# ---------------------------------------------------------------------------
# Invalidation
# ---------------------------------------------------------------------------

class TestInvalidation:
    def test_invalidate_single(self, cache, tmp_path):
        cache.write_table("test:inv", [{"id": "a"}], ttl_days=7, file_subpath="test/inv.csv")
        assert cache.is_valid("test:inv")
        cache.invalidate("test:inv")
        assert not cache.is_valid("test:inv")
        assert not (tmp_path / "test/inv.csv").exists()

    def test_invalidate_all(self, cache, tmp_path):
        cache.write_table("k1", [{"id": "a"}], ttl_days=7, file_subpath="d1/a.csv")
        cache.write_dict("k2", {"x": 1}, ttl_days=7, file_subpath="d2/b.json")
        cache.invalidate_all()
        assert not cache.is_valid("k1")
        assert not cache.is_valid("k2")
        # cache_index.json should still exist
        assert (tmp_path / "cache_index.json").exists()


# ---------------------------------------------------------------------------
# Index and meta files
# ---------------------------------------------------------------------------

class TestIndexAndMeta:
    def test_cache_index_structure(self, cache, tmp_path):
        cache.write_table("test:idx", [{"id": "a"}], ttl_days=7, file_subpath="test/idx.csv")
        with open(tmp_path / "cache_index.json") as f:
            idx = json.load(f)
        assert idx["version"] == _INDEX_VERSION
        assert "test:idx" in idx["entries"]
        entry = idx["entries"]["test:idx"]
        assert entry["path"] == "test/idx.csv"
        assert entry["ttl_days"] == 7
        assert entry["record_count"] == 1

    def test_meta_json_structure(self, cache, tmp_path):
        cache.write_table("test:meta", [{"id": "a"}], ttl_days=7, file_subpath="test/meta.csv")
        with open(tmp_path / "test/.meta.json") as f:
            meta = json.load(f)
        assert "meta.csv" in meta
        assert meta["meta.csv"]["ttl_days"] == 7

    def test_index_persists_across_instances(self, tmp_path):
        c1 = StaticCache(root=tmp_path)
        c1.write_dict("persist", {"x": 1}, ttl_days=30, file_subpath="p/data.json")
        c2 = StaticCache(root=tmp_path)
        assert c2.read_dict("persist") == {"x": 1}


# ---------------------------------------------------------------------------
# Pydantic model round-trip (the real integration test)
# ---------------------------------------------------------------------------

class TestPydanticRoundTrip:
    def test_datasets(self, cache):
        items = [
            DataDatasetItem(id="ds1", name="Brain Sentiment",
                            category={"id": "c1", "name": "Sentiment"},
                            themes=["theme1"], delay=1, region="USA"),
            DataDatasetItem(id="ds2", name="Fundamental",
                            category={"id": "c2", "name": "Fund"},
                            themes=[], delay=1, region="USA"),
        ]
        rows = [item.model_dump(mode="json") for item in items]
        cache.write_table("data:EQUITY:USA:TOP3000:D1:datasets", rows,
                          ttl_days=7, file_subpath="data/EQUITY/USA/TOP3000/D1/datasets.csv")

        back = cache.read_table("data:EQUITY:USA:TOP3000:D1:datasets")
        restored = [DataDatasetItem.model_validate(r) for r in back]
        assert len(restored) == 2
        assert restored[0].id == "ds1"
        assert restored[0].category.name == "Sentiment"
        assert restored[0].themes == ["theme1"]
        assert restored[1].themes == []

    def test_datafields(self, cache):
        items = [
            DataFieldItem(id="field1", type="MATRIX",
                          dataset={"id": "ds1", "name": "Brain"},
                          category={"id": "c1", "name": "Sent"},
                          themes=["t1"]),
        ]
        rows = [item.model_dump(mode="json") for item in items]
        cache.write_table("data:EQUITY:USA:TOP3000:D1:datafields", rows,
                          ttl_days=7, file_subpath="data/EQUITY/USA/TOP3000/D1/datafields.csv")

        back = cache.read_table("data:EQUITY:USA:TOP3000:D1:datafields")
        restored = [DataFieldItem.model_validate(r) for r in back]
        assert restored[0].dataset.name == "Brain"
        assert restored[0].type.value == "MATRIX"

    def test_operators(self, cache):
        items = [
            OperatorItem(name="rank", category="Cross Sectional",
                         scope=["TS", "CS"], definition="rank(x)",
                         description="Ranks values"),
        ]
        rows = [item.model_dump(mode="json") for item in items]
        cache.write_table("operators", rows, ttl_days=30,
                          file_subpath="operators/operators.csv")

        back = cache.read_table("operators")
        restored = [OperatorItem.model_validate(r) for r in back]
        assert restored[0].name == "rank"
        assert restored[0].scope == ["TS", "CS"]

    def test_pyramid_multipliers(self, cache):
        items = [
            PyramidMultiplierItem(
                category={"id": "cat1", "name": "Momentum"},
                region="USA", delay=1, multiplier=1.5),
        ]
        rows = [item.model_dump(mode="json") for item in items]
        cache.write_table("pyramid_multipliers", rows, ttl_days=7,
                          file_subpath="pyramid_multipliers/pyramid_multipliers.csv")

        back = cache.read_table("pyramid_multipliers")
        restored = [PyramidMultiplierItem.model_validate(r) for r in back]
        assert restored[0].category.name == "Momentum"
        assert restored[0].multiplier == 1.5

    def test_platform_settings(self, cache):
        data = {
            "instrument_options": [
                {"instrumentType": "EQUITY", "region": "USA", "delay": 1,
                 "universe": ["TOP3000", "TOP500"], "neutralization": ["SUBINDUSTRY"]}
            ],
            "total_combinations": 1,
            "instrument_types": ["EQUITY"],
            "regions_by_type": {"EQUITY": ["USA"]},
        }
        cache.write_dict("platform_settings", data, ttl_days=30,
                         file_subpath="platform_settings/platform_settings.json")

        back = cache.read_dict("platform_settings")
        restored = SimulationSettingOptionsResponse.model_validate(back)
        assert restored.total_combinations == 1
        assert restored.instrument_options[0].universe == ["TOP3000", "TOP500"]

    def test_documentations(self, cache):
        data = {
            "count": 1, "results": [
                {"id": "tut1", "title": "Getting Started", "category": "basics",
                 "pages": [{"id": "p1", "title": "Intro"}]}
            ]
        }
        cache.write_dict("documentations:index", data, ttl_days=14,
                         file_subpath="documentations/index.json")

        back = cache.read_dict("documentations:index")
        restored = TutorialsResponse.model_validate(back)
        assert restored.results[0].pages[0].title == "Intro"
