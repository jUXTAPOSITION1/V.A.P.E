"""Tests for agents/investigate.py::_scan_privileged_functions() and its
wiring into contract_verification()/write_report() — real gap this closes:
verified source code was already fetched via get_contract_source() (1h
cached, zero extra API cost) but the source_code field itself was
discarded, leaving no insight into constructor/role/treasury functions
even when ownership is renounced now (flagged directly by the user against
investigation-20260725-155143-0xB8d7710f.md). Deliberately informational
only — never wired into score() (see the helper's docstring for why a
text-based function-name scan is too crude to safely score).
"""
from agents import investigate as inv
from tests.conftest import clean_gp, clean_dex


def test_scan_returns_none_without_source():
    assert inv._scan_privileged_functions(None) is None
    assert inv._scan_privileged_functions("") is None
    assert inv._scan_privileged_functions(123) is None


def test_scan_finds_notable_function_names():
    src = """
    contract Foo {
        function mint(address to, uint256 amount) public onlyOwner {}
        function transfer(address to, uint256 amount) public returns (bool) {}
        function setFee(uint256 fee) external onlyOwner {}
    }
    """
    result = inv._scan_privileged_functions(src)
    assert "mint" in result["functions"]
    assert "setFee" in result["functions"]
    assert "transfer" not in result["functions"]


def test_scan_no_notable_functions_returns_empty_list_not_none():
    src = "contract Foo { function balanceOf(address a) public view returns (uint256) {} }"
    result = inv._scan_privileged_functions(src)
    assert result["functions"] == []


def test_scan_detects_selfdestruct():
    src = "contract Foo { function kill() public onlyOwner { selfdestruct(payable(owner)); } }"
    result = inv._scan_privileged_functions(src)
    assert result["has_selfdestruct"] is True
    assert result["has_delegatecall"] is False


def test_scan_detects_delegatecall():
    src = "contract Proxy { function _delegate(address impl) internal { impl.delegatecall(msg.data); } }"
    result = inv._scan_privileged_functions(src)
    assert result["has_delegatecall"] is True


def test_contract_verification_source_code_passthrough_no_key(monkeypatch):
    """The no-DF fallback branch of contract_verification() — hit when
    ETHERSCAN_API_KEY is unset — must return checked=False, not attempt to
    scan anything."""
    monkeypatch.setattr(inv, "DF", None)
    monkeypatch.delenv("ETHERSCAN_API_KEY", raising=False)
    result = inv.contract_verification("0x" + "aa" * 20)
    assert result["checked"] is False


def test_write_report_renders_privileged_function_scan(tmp_path, monkeypatch):
    monkeypatch.setattr(inv, "INVEST_DIR", str(tmp_path))
    gp, onchain = {}, {"is_contract": True}
    dex = clean_dex(symbol="TOKEN")
    verif = {"checked": True, "verified": True, "name": "Foo", "compiler": "v0.8.20",
             "proxy": False, "implementation": None,
             "source_code": "contract Foo { function mint(address to, uint256 amt) public onlyOwner {} }"}
    path, _sym, _emoji = inv.write_report(
        "0x" + "aa" * 20, "8453", gp, dex, onchain, verif, [], 100, "PROCEED", [], [],
    )
    content = open(path).read()
    assert "Notable functions found in verified source (informational, not scored): mint" in content


def test_write_report_privileged_function_scan_honest_when_source_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(inv, "INVEST_DIR", str(tmp_path))
    gp, onchain = {}, {"is_contract": True}
    dex = clean_dex(symbol="TOKEN")
    verif = {"checked": True, "verified": True, "name": "Foo", "compiler": "v0.8.20",
             "proxy": False, "implementation": None}
    path, _sym, _emoji = inv.write_report(
        "0x" + "aa" * 20, "8453", gp, dex, onchain, verif, [], 100, "PROCEED", [], [],
    )
    content = open(path).read()
    assert "Verified source not available to scan this cycle." in content
