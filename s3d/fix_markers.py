"""Recompute each test's simple pytest markers by function name after merging
upstream ceph, so markers git attached to the wrong function by position are
moved back. Git merges by line, so when upstream inserts a test directly above
one carrying an s3d marker, the marker can silently end up on the new test.

usage: fix_markers.py BASE_REF FORK_REF UPSTREAM_REF [--write] [--keep NAME:MARK ...]

BASE_REF is the upstream commit the fork last merged, FORK_REF the fork before
the merge and UPSTREAM_REF the upstream commit being merged. Run it from the
repository root with the merge result in the working tree.
"""
import re
import subprocess
import sys

PREFIX = "src/test/rgw/s3-tests/"
FILES = [PREFIX + "s3tests/functional/test_s3.py", PREFIX + "s3tests/functional/test_headers.py"]
DEF = re.compile(r"^def (\w+)\(")
MARK = re.compile(r"^@pytest\.mark\.(\w+)$")


def show(ref, path):
    r = subprocess.run(["git", "cat-file", "-p", f"{ref}:{path}"], capture_output=True, text=True)
    return r.stdout.split("\n") if r.returncode == 0 else []


def markers(lines):
    """Map each top-level function to the ordered simple markers directly above it."""
    out = {}
    for i, line in enumerate(lines):
        m = DEF.match(line)
        if not m:
            continue
        marks, j = [], i - 1
        while j >= 0 and lines[j].startswith("@"):
            mm = MARK.match(lines[j])
            if mm:
                marks.insert(0, mm.group(1))
            j -= 1
        out[m.group(1)] = marks
    return out


def main():
    base_ref, fork_ref, upstream_ref = sys.argv[1:4]
    write = "--write" in sys.argv
    keep = {}
    if "--keep" in sys.argv:
        for spec in sys.argv[sys.argv.index("--keep") + 1:]:
            name, mark = spec.split(":")
            keep.setdefault(name, []).append(mark)
    total = 0
    for path in FILES:
        base = markers(show(base_ref, path))
        fork = markers(show(fork_ref, path))
        vendor = markers(show(upstream_ref, path))
        lines = open(path).read().split("\n")
        merged = markers(lines)
        expected = {}
        for name, vm in vendor.items():
            if name in fork:
                b = set(base.get(name, []))
                f = fork[name]
                added = [m for m in f if m not in b]
                removed = (b - set(f)) | (b - set(vm))
                exp = [m for m in vm + added if m not in removed]
            else:
                exp = list(vm)
            exp += [m for m in keep.get(name, []) if m not in exp]
            expected[name] = list(dict.fromkeys(exp))
        for name, fm in fork.items():
            if name not in vendor and name in merged:
                # fork-only function (or one ceph dropped that the fork kept)
                expected[name] = list(dict.fromkeys(fm + keep.get(name, [])))
        fixes = {n: e for n, e in expected.items() if n in merged and set(merged[n]) != set(e)}
        for n, e in fixes.items():
            gone = [m for m in merged[n] if m not in e]
            new = [m for m in e if m not in merged[n]]
            print(f"{path}::{n}: drop {gone} add {new}")
        total += len(fixes)
        if write and fixes:
            out, i = [], 0
            while i < len(lines):
                m = DEF.match(lines[i])
                if m and m.group(1) in fixes:
                    # strip the simple markers above this def, keep other decorators
                    j = len(out) - 1
                    others = []
                    while j >= 0 and out[j].startswith("@"):
                        if not MARK.match(out[j]):
                            others.insert(0, out[j])
                        j -= 1
                    del out[j + 1:]
                    out.extend(f"@pytest.mark.{x}" for x in fixes[m.group(1)])
                    out.extend(others)
                out.append(lines[i])
                i += 1
            open(path, "w").write("\n".join(out))
    print(f"{total} functions {'fixed' if write else 'differ'}")


main()
