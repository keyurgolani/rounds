# The corpus driver: pytest plus the framework and the fixtures. It joins
# the stack network and drives the runner and PocketBase; it reuses #9's
# account factory and PocketBase client (harness/probes), so a run uses
# synthetic accounts and never real keys or user data.
#
# Build context is the repository root (set in tests/conformance/compose.yml),
# so both the corpus and the harness client are available to COPY.
FROM python:3.12-slim
WORKDIR /corpus

COPY tests/conformance/requirements.txt /corpus/requirements.txt
RUN pip install --no-cache-dir -r /corpus/requirements.txt

# The framework, the fixtures, the manifest, and the skip ledger.
COPY tests/conformance/ /corpus/
# #9's account factory and PocketBase client.
COPY harness/probes/ /corpus/harness_probes/

ENV PYTHONPATH=/corpus:/corpus/harness_probes \
    PYTHONDONTWRITEBYTECODE=1 \
    CORPUS_RUN=1

# Per-fixture timeouts and the live corpus module. `compose run corpus`
# appends pytest args (e.g. `-k EX-07`) after this entrypoint.
ENTRYPOINT ["python", "-m", "pytest", "-p", "no:cacheprovider", "test_corpus.py", "-rs", "--durations=10"]
