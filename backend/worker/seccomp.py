"""The seccomp filter a worker's init adds on top of the engine's default
profile (ROUNDS-00A-L05).

The engine's default profile stays the container's base. Before any child
runs, init installs this filter on itself, with ``no_new_privs`` set; the
kernel keeps it for init and every process it starts, and none of them can
remove it. On top of the default it:

1. kills any system call made through an architecture other than the
   worker's own, and on x86_64 any call number that carries the x32 bit;
2. kills, with ``SIGSYS``, every call ``DENIED`` marks ``kill``: tracing and
   reading other processes, BPF, the kernel keyring, new namespaces, and
   mounting in every form;
3. answers ``ENOSYS`` to ``io_uring``, so a runtime that probes for it falls
   back instead of dying.

``program(arch)`` builds the classic BPF program from the one table, so the
numbers per architecture and the actions live in a single place, and
tests/test_worker_seccomp.py pins the instruction list. ``install()`` raises
when the kernel refuses; init then runs nothing.
"""
from __future__ import annotations

import ctypes
import errno
import platform

# The calls the filter adds, each with what it answers. One table.
DENIED: tuple[tuple[str, str], ...] = (
    ("ptrace", "kill"),
    ("process_vm_readv", "kill"),
    ("process_vm_writev", "kill"),
    ("bpf", "kill"),
    ("keyctl", "kill"),
    ("add_key", "kill"),
    ("request_key", "kill"),
    ("unshare", "kill"),
    ("setns", "kill"),
    ("mount", "kill"),
    ("umount2", "kill"),
    ("pivot_root", "kill"),
    ("open_tree", "kill"),
    ("move_mount", "kill"),
    ("fsopen", "kill"),
    ("fsconfig", "kill"),
    ("fsmount", "kill"),
    ("fspick", "kill"),
    ("mount_setattr", "kill"),
    ("io_uring_setup", "enosys"),
    ("io_uring_enter", "enosys"),
    ("io_uring_register", "enosys"),
)

# Each call's number per architecture (the kernel's syscall tables:
# arch/x86/entry/syscalls/syscall_64.tbl and include/uapi/asm-generic/unistd.h).
NUMBERS: dict[str, dict[str, int]] = {
    "x86_64": {
        "ptrace": 101, "process_vm_readv": 310, "process_vm_writev": 311, "bpf": 321, "keyctl": 250,
        "add_key": 248, "request_key": 249, "unshare": 272, "setns": 308, "mount": 165, "umount2": 166,
        "pivot_root": 155, "open_tree": 428, "move_mount": 429, "fsopen": 430, "fsconfig": 431, "fsmount": 432,
        "fspick": 433, "mount_setattr": 442, "io_uring_setup": 425, "io_uring_enter": 426,
        "io_uring_register": 427,
    },
    "aarch64": {
        "ptrace": 117, "process_vm_readv": 270, "process_vm_writev": 271, "bpf": 280, "keyctl": 219,
        "add_key": 217, "request_key": 218, "unshare": 97, "setns": 268, "mount": 40, "umount2": 39,
        "pivot_root": 41, "open_tree": 428, "move_mount": 429, "fsopen": 430, "fsconfig": 431, "fsmount": 432,
        "fspick": 433, "mount_setattr": 442, "io_uring_setup": 425, "io_uring_enter": 426,
        "io_uring_register": 427,
    },
}
AUDIT_ARCH = {"x86_64": 0xC000003E, "aarch64": 0xC00000B7}
X32_SYSCALL_BIT = 0x40000000

# Classic BPF, as linux/filter.h and linux/seccomp.h define it.
BPF_LD_W_ABS = 0x20
BPF_JMP_JEQ_K = 0x15
BPF_JMP_JGE_K = 0x35
BPF_RET_K = 0x06
SECCOMP_DATA_NR = 0
SECCOMP_DATA_ARCH = 4
SECCOMP_RET_KILL_PROCESS = 0x80000000
SECCOMP_RET_ERRNO = 0x00050000
SECCOMP_RET_ALLOW = 0x7FFF0000
ACTIONS = {"kill": SECCOMP_RET_KILL_PROCESS, "enosys": SECCOMP_RET_ERRNO | errno.ENOSYS}

PR_SET_NO_NEW_PRIVS = 38
PR_SET_SECCOMP = 22
SECCOMP_MODE_FILTER = 2

Instruction = tuple[int, int, int, int]


class Unsupported(RuntimeError):
    """The filter can't be installed here: another architecture or OS, or
    the kernel refused it."""


def native_arch() -> str:
    machine = platform.machine().lower()
    return {"amd64": "x86_64", "arm64": "aarch64"}.get(machine, machine)


def program(arch: str) -> list[Instruction]:
    """The filter for ``arch`` as ``(code, jt, jf, k)`` instructions."""
    if arch not in NUMBERS:
        raise Unsupported(f"no filter for {arch}")
    numbers = NUMBERS[arch]
    out: list[Instruction] = [
        (BPF_LD_W_ABS, 0, 0, SECCOMP_DATA_ARCH),
        # The worker's own architecture skips the kill that follows.
        (BPF_JMP_JEQ_K, 1, 0, AUDIT_ARCH[arch]),
        (BPF_RET_K, 0, 0, SECCOMP_RET_KILL_PROCESS),
        (BPF_LD_W_ABS, 0, 0, SECCOMP_DATA_NR),
    ]
    if arch == "x86_64":
        # A number at or past the x32 bit falls through to the kill.
        out += [(BPF_JMP_JGE_K, 0, 1, X32_SYSCALL_BIT), (BPF_RET_K, 0, 0, SECCOMP_RET_KILL_PROCESS)]
    for name, action in DENIED:
        out += [(BPF_JMP_JEQ_K, 0, 1, numbers[name]), (BPF_RET_K, 0, 0, ACTIONS[action])]
    out.append((BPF_RET_K, 0, 0, SECCOMP_RET_ALLOW))
    return out


class _SockFilter(ctypes.Structure):
    _fields_ = [("code", ctypes.c_ushort), ("jt", ctypes.c_ubyte), ("jf", ctypes.c_ubyte), ("k", ctypes.c_uint32)]


class _SockFprog(ctypes.Structure):
    _fields_ = [("len", ctypes.c_ushort), ("filter", ctypes.POINTER(_SockFilter))]


def _prctl():
    libc = ctypes.CDLL(None, use_errno=True)
    prctl = libc.prctl
    prctl.argtypes = [ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong]
    prctl.restype = ctypes.c_int
    return prctl


def install(arch: str | None = None) -> None:
    """Sets ``no_new_privs`` and installs the filter on the calling
    process. Raises Unsupported when either step fails."""
    arch = arch or native_arch()
    instructions = program(arch)
    prctl = _prctl()
    if prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0:
        raise Unsupported(f"no_new_privs: {errno.errorcode.get(ctypes.get_errno(), 'error')}")
    filters = (_SockFilter * len(instructions))(*[_SockFilter(*i) for i in instructions])
    fprog = _SockFprog(len(instructions), ctypes.cast(filters, ctypes.POINTER(_SockFilter)))
    if prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, ctypes.addressof(fprog), 0, 0) != 0:
        raise Unsupported(f"seccomp: {errno.errorcode.get(ctypes.get_errno(), 'error')}")


def status(path: str = "/proc/self/status") -> dict[str, str]:
    """The ``NoNewPrivs``, ``Seccomp``, and ``Seccomp_filters`` lines of the
    process's status."""
    out: dict[str, str] = {}
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                key, _, value = line.partition(":")
                if key in ("NoNewPrivs", "Seccomp", "Seccomp_filters"):
                    out[key] = value.strip()
    except OSError:
        pass
    return out
