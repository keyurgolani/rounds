# Bait decoys for the corpus's internal network: a fake metadata
# endpoint, a fake RFC1918 service, and a logging DNS resolver. Standard
# library only, so there is no dependency install and nothing new enters
# the repo's dependency set. The mode is the command's first argument.
FROM python:3.12-slim
WORKDIR /bait
COPY tests/conformance/bait/server.py /bait/server.py
USER 10001:10001
ENTRYPOINT ["python", "/bait/server.py"]
