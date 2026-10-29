import sys; sys.path.insert(0, ".")
from cortexora.data.generate_sample import generate
from cortexora.pipelines.etl import run
from cortexora.config import SAMPLE_DIR
if __name__ == "__main__":
    generate(SAMPLE_DIR); print(run().to_string()); print("ETL OK")
