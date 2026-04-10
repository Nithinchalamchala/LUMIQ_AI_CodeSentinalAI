"""Tests for the buggy calculator — these expose the bugs."""

import pytest
from calculator import add, subtract, multiply, divide, power, factorial, batch_calculate


class TestBasicOperations:
    """Tests for basic arithmetic operations."""

    def test_add(self):
        assert add(2, 3) == 5

    def test_add_negative(self):
        assert add(-1, -2) == -3

    def test_subtract(self):
        assert subtract(10, 3) == 7

    def test_multiply(self):
        assert multiply(4, 5) == 20

    def test_multiply_by_zero(self):
        assert multiply(100, 0) == 0

    def test_divide(self):
        assert divide(10, 2) == 5.0

    def test_divide_by_zero(self):
        """This test exposes the division-by-zero bug."""
        with pytest.raises(ValueError):
            divide(10, 0)

    def test_power(self):
        assert power(2, 3) == 8


class TestFactorial:
    """Tests for factorial function."""

    def test_factorial_zero(self):
        assert factorial(0) == 1

    def test_factorial_one(self):
        assert factorial(1) == 1

    def test_factorial_five(self):
        """This test exposes the off-by-one bug."""
        assert factorial(5) == 120

    def test_factorial_negative(self):
        """This test exposes the missing negative check."""
        with pytest.raises(ValueError):
            factorial(-1)


class TestBatchCalculate:
    """Tests for batch operations."""

    def test_batch_basic(self):
        ops = [("add", (1, 2)), ("multiply", (3, 4))]
        results = batch_calculate(ops)
        assert results == [3, 12]

    def test_batch_empty(self):
        results = batch_calculate([])
        assert results == []

    def test_batch_independent_calls(self):
        """This test exposes the mutable default argument bug.
        Each call should return independent results."""
        r1 = batch_calculate([("add", (1, 1))])
        r2 = batch_calculate([("add", (2, 2))])
        assert len(r2) == 1  # Should be 1, but mutable default makes it 2
