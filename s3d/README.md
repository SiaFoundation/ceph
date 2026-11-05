# s3d

This fork of ceph/ceph carries the s3-tests suite under `src/test/rgw/s3-tests`
for s3d's S3 compatibility tests. Only that directory differs from upstream; the
s3d repository sparse-clones it in CI.

## Changes to s3-tests

- `s3d_unsupported` marks tests for features s3d does not support. s3d runs the
  suite with `-m "not s3d_unsupported and ..."`. Keep the s3d-specific
  changes to that one marker where possible: every extra line is a potential
  conflict when merging upstream.
- `s3tests/functional/__init__.py` aborts pending multipart uploads before
  deleting a bucket and gives the clients a longer read timeout without retries.
- `test_s3.py` carries a few s3d-specific test fixes and additional conditional
  copy tests at the end of the file.

## Syncing with upstream

```sh
git remote add upstream https://github.com/ceph/ceph.git   # once
git fetch upstream main
fork=$(git rev-parse HEAD)
base=$(git merge-base "$fork" upstream/main)
git merge upstream/main
# resolve conflicts under src/test/rgw/s3-tests, then check that the
# s3d_unsupported markers stayed on the right tests:
python3 s3d/fix_markers.py "$base" "$fork" upstream/main
python3 s3d/fix_markers.py "$base" "$fork" upstream/main --write   # to fix
```

GitHub's "Sync fork" button performs the same merge; run the marker check on
the result afterwards. Then run s3d's tox suite against the merged branch and
mark any new tests s3d does not support with `s3d_unsupported`.
