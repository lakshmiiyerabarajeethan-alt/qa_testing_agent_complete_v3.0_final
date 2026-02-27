from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from threading import Event, Lock, Thread
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

LOG_FILE = Path("qa_agent.log")

app = FastAPI(title="QA Testing Agent API")

_lock = Lock()
_state = {
    "running": False,
    "mode": None,
    "started_at": None,
    "ended_at": None,
    "last_report": None,
    "last_error": None,
    "waiting_for_approval": False,
    "approval_excel_path": None,
    "approval_suites": [],
    "log_start_offset": 0,
}

_approval_event = Event()
_approval_decision = None
_approval_lock = Lock()


class RunRequest(BaseModel):
    mode: str = "excel"
    stories_folder: Optional[str] = None
    suite_id: Optional[str] = None
    auto_approve: bool = True
    csv_filename: Optional[str] = None
    excel_filename: Optional[str] = None


class ApprovalRequest(BaseModel):
    decision: str
    details: Optional[str] = None
    merge_to_regression: Optional[bool] = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _set_state(**kwargs) -> None:
    with _lock:
        _state.update(kwargs)


def _run_excel_pipeline(suite_id: Optional[str] = None, excel_filename: Optional[str] = None) -> None:
    try:
        from main import QATestingPipeline

        pipeline = QATestingPipeline()
        report = pipeline.run_from_excel(suite_id=suite_id, excel_filename=excel_filename)
        if report:
            _set_state(last_report=report, last_error=None)
        else:
            _set_state(last_report=None)
    except Exception as exc:
        _set_state(last_error=str(exc))
    finally:
        _set_state(running=False, ended_at=_now_iso())


def _run_csv_pipeline(
    stories_folder: str,
    suite_id: Optional[str],
    auto_approve: bool,
    csv_filename: Optional[str],
) -> None:
    try:
        from main import QATestingPipeline, CSV_STORIES_AVAILABLE

        if not CSV_STORIES_AVAILABLE:
            raise RuntimeError("CSV story reader is not available")

        def _wait_for_approval(excel_path: str) -> str:
            with _approval_lock:
                global _approval_decision
                _approval_decision = None
            _approval_event.clear()
            suite_name = Path(excel_path).name
            mtime = None
            try:
                mtime = Path(excel_path).stat().st_mtime
            except Exception:
                pass
            _set_state(
                waiting_for_approval=True,
                approval_excel_path=excel_path,
                approval_suites=[{"name": suite_name, "mtime": mtime}],
            )
            _approval_event.wait()
            with _approval_lock:
                decision = _approval_decision or "REVISIONS_REQUESTED"
            _set_state(waiting_for_approval=False)
            if decision.upper().startswith("REVISIONS") or decision.upper().startswith("REJECT"):
                _set_state(last_error=f"Approval not granted: {decision}")
            else:
                _set_state(last_error=None)
            return decision

        pipeline = QATestingPipeline()
        report = pipeline.run_from_csv_stories(
            stories_folder=stories_folder,
            suite_id=suite_id,
            auto_approve=auto_approve,
            external_approval_waiter=None if auto_approve else _wait_for_approval,
            csv_filename=csv_filename,
        )
        if report:
            _set_state(last_report=report, last_error=None)
        else:
            _set_state(last_report=None)
    except Exception as exc:
        _set_state(last_error=str(exc))
    finally:
        _set_state(running=False, ended_at=_now_iso())


@app.post("/api/run")
def api_run(req: RunRequest):
    with _lock:
        if _state["running"]:
            raise HTTPException(status_code=409, detail="Pipeline already running")
        log_start = LOG_FILE.stat().st_size if LOG_FILE.exists() else 0
        _state["running"] = True
        _state["mode"] = req.mode
        _state["started_at"] = _now_iso()
        _state["ended_at"] = None
        _state["last_error"] = None
        _state["waiting_for_approval"] = False
        _state["approval_excel_path"] = None
        _state["approval_suites"] = []
        _state["log_start_offset"] = log_start

    if req.mode == "excel":
        t = Thread(target=_run_excel_pipeline, args=(req.suite_id, req.excel_filename), daemon=True)
    elif req.mode == "csv":
        folder = req.stories_folder or "./stories"
        t = Thread(
            target=_run_csv_pipeline,
            args=(folder, req.suite_id, req.auto_approve, req.csv_filename),
            daemon=True,
        )
    else:
        _set_state(running=False, ended_at=_now_iso(), last_error="Invalid mode")
        raise HTTPException(status_code=400, detail="Invalid mode")
    t.start()
    return api_status()


@app.get("/api/status")
def api_status():
    with _lock:
        report_path = _state.get("last_report") or None
        report_url = None
        if report_path:
            report_url = f"/reports/{Path(report_path).name}"
        log_size = LOG_FILE.stat().st_size if LOG_FILE.exists() else 0
        return {
            "running": _state["running"],
            "mode": _state["mode"],
            "started_at": _state["started_at"],
            "ended_at": _state["ended_at"],
            "last_report": report_path,
            "report_url": report_url,
            "last_error": _state.get("last_error"),
            "log_size": log_size,
            "waiting_for_approval": _state.get("waiting_for_approval"),
            "approval_excel_path": _state.get("approval_excel_path"),
            "approval_suites": _state.get("approval_suites") or [],
            "log_start_offset": _state.get("log_start_offset", 0),
        }


@app.get("/api/suites")
def api_suites():
    try:
        from parsers.excel_parser import TestCaseParser
        parser = TestCaseParser("./test_inputs")
        files = parser.list_excel_files()
        return {"files": files}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/open_suite")
def api_open_suite(filename: str):
    if not filename:
        raise HTTPException(status_code=400, detail="Filename required")
    safe_name = Path(filename).name
    target = Path("./test_inputs") / safe_name
    if not target.exists():
        raise HTTPException(status_code=404, detail="Suite not found")
    try:
        from utils.approval_workflow import ManualApprovalHelper
        ManualApprovalHelper.open_excel_file(str(target))
        return {"ok": True, "path": str(target)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/approval")
def api_approval(req: ApprovalRequest):
    with _lock:
        if not _state["running"] or not _state.get("waiting_for_approval"):
            raise HTTPException(status_code=409, detail="No approval pending")

    decision = req.decision.strip().upper()
    if decision in ["APPROVE", "APPROVED", "1"]:
        merge_flag = req.merge_to_regression
        if merge_flag is False:
            decision_str = "APPROVED|MERGE=0"
        else:
            decision_str = "APPROVED"
    elif decision in ["REJECT", "REJECTED", "3"]:
        details = (req.details or "").strip()
        decision_str = f"REJECTED: {details or 'Rejected via API'}"
    elif decision in ["REVISE", "REVISIONS", "REVISION", "4", "REQUEST_REVISION"]:
        details = (req.details or "").strip()
        decision_str = f"REVISIONS_REQUESTED: {details or 'Revisions requested via API'}"
    else:
        raise HTTPException(status_code=400, detail="Invalid decision")

    with _approval_lock:
        global _approval_decision
        _approval_decision = decision_str
    _approval_event.set()
    return {"ok": True, "decision": decision_str}


@app.get("/api/logs")
def api_logs(offset: int = 0, max_bytes: int = 200000):
    if offset < 0:
        offset = 0
    if max_bytes < 1:
        max_bytes = 1
    if not LOG_FILE.exists():
        return {"offset": 0, "chunk": ""}

    with LOG_FILE.open("rb") as f:
        f.seek(offset)
        data = f.read(max_bytes)
        new_offset = f.tell()

    return {
        "offset": new_offset,
        "chunk": data.decode("utf-8", errors="replace"),
    }


# API routes must be registered before static mounts.
app.mount("/reports", StaticFiles(directory="reports"), name="reports")
app.mount("/", StaticFiles(directory=".", html=True), name="static")
