from __future__ import annotations

import re

from ....host import Controller
from . import get_binary
from . import launch_to
from . import pwndbg_test

HEAP_TCACHEVIS = get_binary("heap_tcachevis.native.out")

ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")


def strip_colors(text: str) -> str:
    return ANSI_ESCAPE.sub("", text)


async def tcache_bucket_counts(ctrl: Controller) -> dict[int, int]:
    """Expected (chunk size -> count) mapping, computed like the command does."""
    import pwndbg.aglib.heap.glibc
    import pwndbg.aglib.memory
    import pwndbg.aglib.symbol

    allocator = pwndbg.aglib.heap.glibc.get_allocator()

    result = {}
    for name in ("a", "b", "c"):
        size_addr = pwndbg.aglib.symbol.lookup_symbol_addr(f"size_{name}")
        count_addr = pwndbg.aglib.symbol.lookup_symbol_addr(f"count_{name}")
        assert size_addr is not None and count_addr is not None
        size = allocator._request2size(pwndbg.aglib.memory.u64(size_addr))
        count = pwndbg.aglib.memory.u64(count_addr)
        result[size] = count
    return result


@pwndbg_test
async def test_tcachevis_empty(ctrl: Controller) -> None:
    """The tcache is empty at the first break_here (no frees happened yet)."""
    await launch_to(ctrl, HEAP_TCACHEVIS, "break_here")
    await ctrl.execute("set width 0")

    out = strip_colors(await ctrl.execute_and_capture("tcachevis"))

    assert "tcachevis" in out
    assert "tcache is pointing to:" in out
    assert "empty" in out


@pwndbg_test
async def test_tcachevis_buckets(ctrl: Controller) -> None:
    """After the frees, each size bucket shows its count, bar and chain."""
    import pwndbg.aglib.heap.glibc

    await launch_to(ctrl, HEAP_TCACHEVIS, "break_here")
    await ctrl.execute("set width 0")
    await ctrl.cont()

    expected = await tcache_bucket_counts(ctrl)
    assert len(expected) == 3

    out = strip_colors(await ctrl.execute_and_capture("tcachevis"))
    lines = out.splitlines()

    assert "tcachevis" in lines[0]
    assert any("tcache is pointing to:" in line for line in lines)

    # tcache bins hold at most mp_.tcache_count chunks (7 by default)
    max_slots = int(pwndbg.aglib.heap.glibc.get_allocator().mp["tcache_count"])

    for size, count in expected.items():
        bucket_lines = [line for line in lines if line.startswith(hex(size))]
        assert len(bucket_lines) == 1, f"missing bucket for size {hex(size)}"
        line = bucket_lines[0]

        # count is shown as [count/max_slots]
        assert f"[{count:3d}/{max_slots:3d}]" in line

        # the bar is proportional to the fill level and never exceeds the width
        bar = re.search(r"[█░]+", line)
        assert bar is not None
        assert len(bar.group(0)) == 32
        assert bar.group(0).count("█") == round(count * 32 / max_slots)

        # the chain lists exactly `count` chunk addresses
        assert line.count("—▸") == count - 1


@pwndbg_test
async def test_tcachevis_verbose_and_width(ctrl: Controller) -> None:
    """-v shows empty buckets and -w controls the bar width."""
    await launch_to(ctrl, HEAP_TCACHEVIS, "break_here")
    await ctrl.execute("set width 0")
    await ctrl.cont()

    expected = await tcache_bucket_counts(ctrl)

    out = strip_colors(await ctrl.execute_and_capture("tcachevis -v -w 10"))
    lines = out.splitlines()

    # verbose shows buckets that have no chunks, on top of the filled ones
    bucket_lines = [line for line in lines if re.match(r"0x[0-9a-f]+ ", line)]
    assert len(bucket_lines) > len(expected)
    assert any("[  0/" in line for line in bucket_lines)

    # all bars respect the requested width
    for line in bucket_lines:
        bar = re.search(r"[█░]+", line)
        assert bar is not None
        assert len(bar.group(0)) == 10


@pwndbg_test
async def test_tcachevis_explicit_tcache_address(ctrl: Controller) -> None:
    """Passing the tcache address explicitly works like the tcachebins command."""
    import pwndbg.aglib.heap.glibc

    await launch_to(ctrl, HEAP_TCACHEVIS, "break_here")
    await ctrl.execute("set width 0")
    await ctrl.cont()

    tcache = pwndbg.aglib.heap.glibc.get_allocator().get_tcache()
    assert tcache is not None

    implicit = strip_colors(await ctrl.execute_and_capture("tcachevis"))
    explicit = strip_colors(await ctrl.execute_and_capture(f"tcachevis {int(tcache.address)}"))

    assert implicit == explicit
