"""Tests for agents/intel_common.py's safe formatting helpers. Small, but
they exist specifically because a raw f-string format spec crashes on the
'unavailable'/None values every real fetcher degrades to — these pin the
never-crash contract."""
from unittest import mock

from agents import intel_common as ic


def test_fmt_usd_whole_dollars():
    assert ic.fmt_usd(1234) == "$1,234"
    assert ic.fmt_usd(1234.99) == "$1,235"
    assert ic.fmt_usd(0) == "$0"


def test_fmt_usd_survives_non_numeric():
    assert ic.fmt_usd(None) == "unavailable"
    assert ic.fmt_usd("—") == "unavailable"
    assert ic.fmt_usd("error") == "unavailable"


def test_fmt_price_precision_by_scale():
    assert ic.fmt_price(0.5707) == "$0.5707"     # sub-$1 keeps precision
    assert ic.fmt_price(12.5) == "$12.50"        # >=$1 collapses to cents
    assert ic.fmt_price(0) == "$0.0000"


def test_fmt_price_survives_non_numeric():
    assert ic.fmt_price(None) == "unavailable"
    assert ic.fmt_price("n/a") == "unavailable"


def test_bool_is_not_treated_as_number():
    # isinstance(True, int) is True in Python — make sure the helpers don't
    # accidentally format a bool as "$1"; documenting whatever the real
    # contract is so a future refactor can't silently change it.
    # (bools are ints in Python, so this currently formats — pin it.)
    assert ic.fmt_usd(True) == "$1"


def test_grok_analysis_defaults_search_true():
    """search=True is grok_analysis()'s default — the 4 report generators
    that call it with no explicit `search` kwarg (broadcast.py,
    bug_bounty_intel.py, mainnet_patch_check.py, skillforge/toolcheck.py)
    must inherit Live Search without needing their own edit."""
    with mock.patch("agents.llm.ask_oci_grok_safe", return_value=("analysis text", "xai_1")) as m:
        ic.grok_analysis("analyst", "some real grounding data")
    assert m.call_args.kwargs["search"] is True


def test_grok_analysis_forwards_explicit_search_false():
    with mock.patch("agents.llm.ask_oci_grok_safe", return_value=("analysis text", "xai_1")) as m:
        ic.grok_analysis("analyst", "some real grounding data", search=False)
    assert m.call_args.kwargs["search"] is False
