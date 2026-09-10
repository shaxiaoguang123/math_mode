"""Observe local process identities without treating a reused PID as its owner."""
import os
import math

import psutil


def identity(pid=None):
    process = psutil.Process(os.getpid() if pid is None else pid)
    return {"pid": process.pid, "create_time": process.create_time()}


def stopped(record):
    if set(record) != {"pid", "create_time"} or type(record["pid"]) is not int or record["pid"] <= 0:
        raise ValueError("Missing/invalid process identity; legacy ownership cannot be inferred")
    stamp = record["create_time"]
    if stamp is not None and (type(stamp) not in {int, float} or not math.isfinite(stamp) or stamp <= 0):
        raise ValueError("Invalid process creation time")
    try:
        process = psutil.Process(record["pid"])
        return (record["create_time"] is not None and process.create_time() != record["create_time"]) or process.status() == psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return True
    except psutil.AccessDenied as exc:
        raise ValueError("Process state cannot be verified with current permissions") from exc
