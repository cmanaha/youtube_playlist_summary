import pytest
from typing import Optional
from transcript_processor import TranscriptProcessor

def test_transcript_processor_initialization() -> None:
    processor = TranscriptProcessor(
        batch_size=2,
        num_gpus=0,
        num_cpus=4,
        model='llama2',
        num_threads=4
    )
    assert processor.batch_size == 2
    assert processor.llm is not None
    assert processor.batch_size == 2
    assert processor.valid_categories is not None
    assert processor.filter_categories is None

def test_category_filtering():
    processor = TranscriptProcessor()
    processor.set_filter_categories("Security,AI & ML")
    assert processor.filter_categories == {"security", "ai & ml"}

def test_category_case_insensitive():
    processor = TranscriptProcessor()
    processor.set_filter_categories("security,AI & ML")
    assert processor.filter_categories == {"security", "ai & ml"} 