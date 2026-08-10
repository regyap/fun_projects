import pytest
from pydantic import ValidationError

from domain.job import JobCreate


def test_valid_job():
    job = JobCreate(task="calculate", number=5)
    assert job.number == 5


def test_invalid_task():
    with pytest.raises(ValidationError):
        JobCreate(task="shell", number=5)


def test_negative_number_rejected():
    with pytest.raises(ValidationError):
        JobCreate(task="calculate", number=-1)
