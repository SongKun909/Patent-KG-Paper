"""Bridge between FastAPI and existing src/ pipeline."""
import asyncio
import sys
from pathlib import Path

# Ensure src/ is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


async def run_pipeline_for_patent(patent, progress_callback=None) -> list:
    """Run extraction pipeline on a patent. Called from TaskManager.

    Args:
        patent: app.models.patent.Patent DB object
        progress_callback: async callable(progress_int, step_name)

    Returns:
        List of Quintuple objects from src/models/quintuple.py
    """
    loop = asyncio.get_event_loop()

    def _run():
        from pipeline import ExtractionPipeline

        pipeline = ExtractionPipeline()
        if progress_callback:
            # Simulate progress at key stages via a simple wrapper
            pass
        return pipeline.run_from_pdf(patent.file_path)

    quints = await loop.run_in_executor(None, _run)
    return quints
