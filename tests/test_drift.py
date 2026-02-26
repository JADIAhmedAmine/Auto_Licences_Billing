from m365_billing.audit.drift import drift_audit


def test_ok():
    a = drift_audit(qty_new=110, qty_prev=100, warn_thr=0.5, crit_thr=2.0)
    assert a["status"] == "ok"


def test_warning():
    a = drift_audit(qty_new=200, qty_prev=100, warn_thr=0.5, crit_thr=2.0)
    assert a["status"] == "warning"


def test_critical():
    a = drift_audit(qty_new=400, qty_prev=100, warn_thr=0.5, crit_thr=2.0)
    assert a["status"] == "critical"
