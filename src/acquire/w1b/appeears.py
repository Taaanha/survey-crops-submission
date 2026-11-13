"""Small AppEEARS client (login, submit, wait, download) for the Colab notebook.

AppEEARS API documentation: https://appeears.earthdatacloud.nasa.gov/api/ . The Earthdata username
and password are typed into the notebook (getpass) and only used for the login call; the bearer
token is kept in memory. Nothing here prints or saves a credential."""

import os
import time

from w1b.products import APPEEARS_API

PENDING_STATES = ("pending", "queued", "processing")


def login(session, username, password, api=APPEEARS_API):
    """Bearer token for AppEEARS from an Earthdata username and password."""
    r = session.post(f"{api}/login", auth=(username, password), timeout=60)
    r.raise_for_status()
    return r.json()["token"]


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def submit(session, token, task, api=APPEEARS_API):
    """Submit a task body from products.area_task; returns the task id."""
    r = session.post(f"{api}/task", json=task, headers=_headers(token), timeout=120)
    r.raise_for_status()
    return r.json()["task_id"]


def wait(session, token, task_id, poll_s=30, max_wait_s=6 * 3600, api=APPEEARS_API, sleep=time.sleep):
    """Poll until the task is done. Returns 'done'; raises RuntimeError on error or timeout."""
    waited = 0
    while True:
        r = session.get(f"{api}/task/{task_id}", headers=_headers(token), timeout=60)
        r.raise_for_status()
        status = r.json().get("status", "")
        if status == "done":
            return status
        if status not in PENDING_STATES:
            raise RuntimeError(f"AppEEARS task {task_id} ended with status {status!r}")
        if waited >= max_wait_s:
            raise RuntimeError(f"AppEEARS task {task_id} still {status!r} after {max_wait_s} s")
        sleep(poll_s)
        waited += poll_s


def list_files(session, token, task_id, suffixes=(".nc",), api=APPEEARS_API):
    """[(file_id, file_name, file_size)] of the task's output files with one of `suffixes`."""
    r = session.get(f"{api}/bundle/{task_id}", headers=_headers(token), timeout=60)
    r.raise_for_status()
    return [(f["file_id"], os.path.basename(f["file_name"]), f.get("file_size"))
            for f in r.json().get("files", []) if f["file_name"].lower().endswith(tuple(suffixes))]


def download(session, token, task_id, file_id, dest_path, api=APPEEARS_API):
    """Stream one output file to dest_path (via a .part file); returns dest_path."""
    os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
    tmp = dest_path + ".part"
    with session.get(f"{api}/bundle/{task_id}/{file_id}", headers=_headers(token),
                     stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(tmp, "wb") as fh:
            for chunk in r.iter_content(chunk_size=1 << 20):
                fh.write(chunk)
    os.replace(tmp, dest_path)
    return dest_path
