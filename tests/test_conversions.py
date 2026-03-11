import numpy as np
import pytest
from numpy.testing import assert_allclose

from stk_files._validation import (
    _dcm_to_quaternions,
    _euler_to_quaternions,
    _quat_multiply,
)


class TestQuatMultiply:
    def test_identity_left(self) -> None:
        identity = np.array([0.0, 0.0, 0.0, 1.0])
        q = np.array([0.1, 0.2, 0.3, 0.9])
        q = q / np.linalg.norm(q)
        result = _quat_multiply(identity, q)
        assert_allclose(result, q, atol=1e-12)

    def test_identity_right(self) -> None:
        identity = np.array([0.0, 0.0, 0.0, 1.0])
        q = np.array([0.1, 0.2, 0.3, 0.9])
        q = q / np.linalg.norm(q)
        result = _quat_multiply(q, identity)
        assert_allclose(result, q, atol=1e-12)

    def test_inverse(self) -> None:
        """q * conj(q) = identity."""
        q = np.array([0.5, 0.5, 0.5, 0.5])
        q_conj = np.array([-0.5, -0.5, -0.5, 0.5])
        result = _quat_multiply(q, q_conj)
        assert_allclose(result, [0, 0, 0, 1], atol=1e-12)

    def test_unit_norm_preserved(self) -> None:
        q1 = np.array([0.1, 0.2, 0.3, 0.9])
        q1 = q1 / np.linalg.norm(q1)
        q2 = np.array([0.4, 0.5, 0.6, 0.4])
        q2 = q2 / np.linalg.norm(q2)
        result = _quat_multiply(q1, q2)
        assert_allclose(np.linalg.norm(result), 1.0, atol=1e-12)


class TestEulerToQuaternions:
    def test_zero_angles(self) -> None:
        """Zero angles -> identity quaternion."""
        data = np.array([[0.0, 0.0, 0.0]])
        result = _euler_to_quaternions(data, 321)
        assert_allclose(result[0], [0, 0, 0, 1], atol=1e-12)

    def test_90_deg_single_axis(self) -> None:
        """90 degrees about z-axis (sequence 321, only yaw)."""
        data = np.array([[90.0, 0.0, 0.0]])
        result = _euler_to_quaternions(data, 321)
        # For 321 sequence, first angle rotates about axis 3 (z)
        expected_w = np.cos(np.pi / 4)
        expected_z = np.sin(np.pi / 4)
        assert_allclose(np.abs(result[0, 3]), expected_w, atol=1e-10)
        assert_allclose(np.abs(result[0, 2]), expected_z, atol=1e-10)
        # x and y should be zero
        assert_allclose(result[0, 0], 0.0, atol=1e-10)
        assert_allclose(result[0, 1], 0.0, atol=1e-10)

    def test_output_is_unit_norm(self) -> None:
        """All output quaternions should be unit norm."""
        data = np.array(
            [
                [10.0, 20.0, 30.0],
                [45.0, -30.0, 60.0],
                [180.0, 0.0, 0.0],
            ]
        )
        result = _euler_to_quaternions(data, 123)
        norms = np.sqrt(np.sum(result**2, axis=1))
        assert_allclose(norms, 1.0, atol=1e-12)

    @pytest.mark.parametrize("seq", [121, 123, 131, 132, 212, 213, 231, 232, 312, 313, 321, 323])
    def test_all_euler_sequences_identity(self, seq: int) -> None:
        """Zero angles should give identity for all sequences."""
        data = np.array([[0.0, 0.0, 0.0]])
        result = _euler_to_quaternions(data, seq)
        assert_allclose(result[0], [0, 0, 0, 1], atol=1e-12)


class TestDcmToQuaternions:
    def test_identity_matrix(self) -> None:
        """Identity DCM -> identity quaternion."""
        data = np.array([[1, 0, 0, 0, 1, 0, 0, 0, 1]], dtype=np.float64)
        result = _dcm_to_quaternions(data)
        # Either [0,0,0,1] or [0,0,0,-1] are valid
        assert_allclose(np.abs(result[0, 3]), 1.0, atol=1e-10)
        assert_allclose(result[0, :3], 0.0, atol=1e-10)

    def test_180_deg_about_z(self) -> None:
        """180 deg rotation about z."""
        data = np.array([[-1, 0, 0, 0, -1, 0, 0, 0, 1]], dtype=np.float64)
        result = _dcm_to_quaternions(data)
        norm = np.linalg.norm(result[0])
        assert_allclose(norm, 1.0, atol=1e-10)
        # Should be [0, 0, +-1, 0]
        assert_allclose(np.abs(result[0, 2]), 1.0, atol=1e-10)

    def test_90_deg_about_x(self) -> None:
        """90 deg rotation about x-axis."""
        data = np.array([[1, 0, 0, 0, 0, -1, 0, 1, 0]], dtype=np.float64)
        result = _dcm_to_quaternions(data)
        norm = np.linalg.norm(result[0])
        assert_allclose(norm, 1.0, atol=1e-10)

    def test_output_is_unit_norm(self) -> None:
        """Random orthogonal matrices should give unit quaternions."""
        # Simple rotation about y-axis by 45 degrees
        c = np.cos(np.pi / 4)
        s = np.sin(np.pi / 4)
        data = np.array([[c, 0, s, 0, 1, 0, -s, 0, c]], dtype=np.float64)
        result = _dcm_to_quaternions(data)
        assert_allclose(np.linalg.norm(result[0]), 1.0, atol=1e-10)
