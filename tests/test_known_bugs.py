"""
Regression tests for known bugs that caused Docker rebuilds during Phase 7.

Each test corresponds to a VIA_NEGATIVA case ID. These tests are pure
Python/data logic — no GPU, no model weights, no GCS access required.

Run with:
    python3 -m pytest tests/test_known_bugs.py -v
    python3 tests/test_known_bugs.py
"""

import os
import tarfile
import tempfile

import pytest


# ============================================================
# Bug 1: Empty shard tolerance (C-003)
# VIA_NEGATIVA: WebDataset opening an empty/corrupt .tar must not crash.
# load_shard() should return None for empty shards.
# ============================================================

class TestEmptyShardTolerance:
    """C-003: Empty/corrupt .tar shard must not crash the process."""

    def test_empty_tar_returns_none(self, tmp_path):
        """An empty .tar file (0 bytes) should be handled gracefully."""
        wds = pytest.importorskip("webdataset")

        empty_tar = tmp_path / "omega_shard_0000.tar"
        empty_tar.write_bytes(b"")

        def load_shard(path):
            """Simulate shard loading with empty-shard tolerance."""
            try:
                dataset = wds.WebDataset(
                    [str(path)], resampled=False,
                    handler=wds.warn_and_continue,
                )
                samples = list(dataset)
                if len(samples) == 0:
                    return None
                return samples
            except Exception:
                return None

        result = load_shard(empty_tar)
        assert result is None, "Empty .tar must return None, not crash"

    def test_corrupt_tar_returns_none(self, tmp_path):
        """A .tar with garbage bytes should be handled gracefully."""
        wds = pytest.importorskip("webdataset")

        corrupt_tar = tmp_path / "omega_shard_9999.tar"
        corrupt_tar.write_bytes(b"\x00\xff\xfe\xfd" * 100)

        def load_shard(path):
            try:
                dataset = wds.WebDataset(
                    [str(path)], resampled=False,
                    handler=wds.warn_and_continue,
                )
                samples = list(dataset)
                if len(samples) == 0:
                    return None
                return samples
            except Exception:
                return None

        result = load_shard(corrupt_tar)
        assert result is None, "Corrupt .tar must return None, not crash"

    def test_valid_tar_returns_samples(self, tmp_path):
        """A valid .tar with content should return samples (not None)."""
        wds = pytest.importorskip("webdataset")

        # Create a valid .tar with a dummy sample
        tar_path = tmp_path / "omega_shard_0001.tar"
        with tarfile.open(str(tar_path), "w") as tf:
            import io
            data = b"hello"
            info = tarfile.TarInfo(name="sample_000.txt")
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))

        def load_shard(path):
            try:
                dataset = wds.WebDataset(
                    [str(path)], resampled=False,
                    handler=wds.warn_and_continue,
                )
                samples = list(dataset)
                if len(samples) == 0:
                    return None
                return samples
            except Exception:
                return None

        result = load_shard(tar_path)
        assert result is not None, "Valid .tar should return samples"


# ============================================================
# Bug 2: Single sample squeeze -> dimension collapse (C-008)
# VIA_NEGATIVA: preds.squeeze() on [1]-shaped tensor collapses to
# scalar [], breaking .tolist(). Use preds.view(-1) instead.
# ============================================================

class TestSingleSampleSqueeze:
    """C-008: squeeze() on [1]-shaped tensor collapses dimension."""

    def test_squeeze_collapses_single_sample(self):
        """Demonstrate the bug: squeeze() on shape [1] -> scalar []."""
        torch = pytest.importorskip("torch")

        preds = torch.tensor([42.0])  # shape [1]
        squeezed = preds.squeeze()

        assert squeezed.shape == torch.Size([]), (
            "squeeze() should collapse [1] to [] (this is the bug)"
        )
        assert squeezed.ndim == 0, "squeeze() produces a 0-dim scalar"

    def test_view_minus1_preserves_dimension(self):
        """The fix: view(-1) preserves [1] shape for single samples."""
        torch = pytest.importorskip("torch")

        preds = torch.tensor([42.0])  # shape [1]
        fixed = preds.view(-1)

        assert fixed.shape == torch.Size([1]), (
            "view(-1) must preserve [1] shape"
        )
        assert fixed.ndim == 1, "view(-1) keeps 1-dim"

    def test_view_minus1_works_for_batches(self):
        """view(-1) also works correctly for normal batch sizes."""
        torch = pytest.importorskip("torch")

        preds = torch.randn(512)  # normal batch
        fixed = preds.view(-1)

        assert fixed.shape == torch.Size([512])

    def test_tolist_after_view_works(self):
        """After view(-1), .tolist() returns a list (not a scalar)."""
        torch = pytest.importorskip("torch")

        preds = torch.tensor([42.0])
        result = preds.view(-1).tolist()

        assert isinstance(result, list), ".tolist() on view(-1) must return list"
        assert len(result) == 1

    def test_numpy_ndim_after_squeeze_is_zero(self):
        """The same bug manifests in numpy: .squeeze() on shape (1,) -> ()."""
        torch = pytest.importorskip("torch")
        import numpy as np

        preds = torch.tensor([42.0])
        pred_bp = (preds.squeeze() * 216.24 + (-5.08)).numpy().copy()

        assert pred_bp.ndim == 0, "numpy scalar from squeeze has ndim 0"
        # This is the actual crash path in phase7_inference.py line 313:
        # pred_bp[i] fails when pred_bp is a 0-dim array and i > 0


# ============================================================
# Bug 3: Iterator exception caught (C-009)
# VIA_NEGATIVA: WebDataset iterator can raise ValueError inside
# `for sample in dataset` (not at iter() time). The try/except
# must wrap the entire for-loop body.
# ============================================================

class TestIteratorExceptionCaught:
    """C-009: ValueError during iteration must be caught, not crash."""

    def test_exception_inside_iteration_is_caught(self):
        """Mock dataset that raises ValueError mid-iteration."""

        class ExplodingDataset:
            """Simulates a WebDataset that raises during iteration."""
            def __iter__(self):
                yield {"__key__": "good_sample", "data": 1}
                raise ValueError("corrupt sample in shard")

        dataset = ExplodingDataset()
        collected = []
        errors = []

        # Correct pattern: try/except wraps the for-loop
        try:
            for sample in dataset:
                collected.append(sample)
        except (ValueError, Exception) as e:
            errors.append(str(e))

        assert len(collected) == 1, "Should have collected the good sample"
        assert len(errors) == 1, "Should have caught the ValueError"
        assert "corrupt sample" in errors[0]

    def test_exception_only_at_iter_misses_mid_loop_errors(self):
        """Demonstrate that wrapping only iter() is insufficient."""

        class ExplodingDataset:
            def __iter__(self):
                yield {"__key__": "good_sample", "data": 1}
                raise ValueError("corrupt sample in shard")

        dataset = ExplodingDataset()

        # WRONG pattern: try/except only around iter()
        # This would NOT catch the ValueError raised during iteration
        try:
            it = iter(dataset)
        except ValueError:
            pytest.fail("ValueError should not be raised at iter() time")

        # The error comes during next() calls, not iter()
        items = []
        items.append(next(it))  # This works fine

        with pytest.raises(ValueError, match="corrupt sample"):
            next(it)  # This is where it explodes


# ============================================================
# Bug 4: SSH pipe stdin conflict
# VIA_NEGATIVA: `while read line; do ssh ...; done < file` causes
# ssh to steal stdin. Fix: `mapfile -t arr < file; for x in
# "${arr[@]}"; do ssh -n ...; done`
# This is a bash pattern — documented as a comment-only test.
# ============================================================

class TestSSHPipeStdinConflict:
    """SSH stdin conflict: bash pattern, documented as comment-only test."""

    def test_documented_rule(self):
        """
        BASH BUG (not testable in Python):

        WRONG:
            while read line; do
                ssh user@host "command $line"
            done < file.txt
            # ssh steals stdin from the while-read loop -> only processes 1 line

        CORRECT:
            mapfile -t arr < file.txt
            for x in "${arr[@]}"; do
                ssh -n user@host "command $x"
            done
            # mapfile reads all lines first; ssh -n prevents stdin theft

        See VIA_NEGATIVA.md "SSH pipe parallel upload" entry.
        """
        pass  # Comment-only test — the docstring IS the test


# ============================================================
# Bug 5: Upload verification — file size must be > 0 after upload
# VIA_NEGATIVA: SSH pipe uploads can create 0-byte files silently.
# Every upload must verify size > 0.
# ============================================================

class TestUploadVerification:
    """Upload verification: file size must be checked > 0 after upload."""

    def test_zero_byte_file_fails_verification(self, tmp_path):
        """A 0-byte file must fail upload verification."""
        zero_file = tmp_path / "omega_shard_0001.tar"
        zero_file.write_bytes(b"")

        assert not verify_upload(str(zero_file)), (
            "0-byte file must fail verification"
        )

    def test_normal_file_passes_verification(self, tmp_path):
        """A file with content must pass upload verification."""
        good_file = tmp_path / "omega_shard_0001.tar"
        good_file.write_bytes(b"\x00" * 1024)

        assert verify_upload(str(good_file)), (
            "Non-empty file must pass verification"
        )

    def test_missing_file_fails_verification(self):
        """A file that doesn't exist must fail verification."""
        assert not verify_upload("/nonexistent/path/shard.tar"), (
            "Missing file must fail verification"
        )


def verify_upload(path: str) -> bool:
    """
    Post-upload verification: file must exist and have size > 0.

    This is the pattern that must be applied after every GCS/SSH upload.
    476/1992 shards were corrupted as 0-byte files when this check was missing.
    """
    try:
        return os.path.getsize(path) > 0
    except OSError:
        return False


# ============================================================
# Direct execution support
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
